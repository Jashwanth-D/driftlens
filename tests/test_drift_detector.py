import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai"))

from drift_detector import DriftReport, narrate_drift, detect_s3_drift, detect_lambda_drift, detect_storage_drift, run_cmd
from unittest.mock import patch, MagicMock


def test_drift_report_no_drift():
    r = DriftReport(resource_type="AWS S3", resource_name="my-bucket", has_drift=False, diffs=[], narrative="All good.")
    assert r.has_drift is False
    assert r.diffs == []
    assert r.resource_type == "AWS S3"


def test_drift_report_with_drift():
    r = DriftReport(resource_type="AWS Lambda", resource_name="my-fn", has_drift=True,
                    diffs=["Memory: 128 -> 256"], narrative="Memory drifted.")
    assert r.has_drift is True
    assert len(r.diffs) == 1


def test_drift_report_multiple_diffs():
    r = DriftReport(resource_type="Azure Storage", resource_name="acct", has_drift=True,
                    diffs=["Tier changed", "Replication changed", "Tags changed"], narrative="Multiple.")
    assert len(r.diffs) == 3


def test_narrate_drift_no_diffs_shortcircuits():
    result = narrate_drift("AWS S3", "any-bucket", [])
    assert "No drift" in result


def test_narrate_drift_calls_groq_when_diffs_exist():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "The Lambda memory was manually increased."
    with patch("drift_detector.client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = narrate_drift("AWS Lambda", "my-fn", ["Memory: 128 -> 256"])
        assert "Lambda memory" in result
        mock_client.chat.completions.create.assert_called_once()


def test_narrate_drift_strips_think_tags():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "<think>reasoning here</think>Final narrative text."
    with patch("drift_detector.client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = narrate_drift("AWS S3", "b", ["something"])
        assert "reasoning" not in result
        assert "Final narrative text." in result


def test_detect_lambda_drift_no_drift():
    tf_state = {
        "values": {
            "root_module": {
                "resources": [
                    {"type": "aws_lambda_function", "name": "hello", "values": {
                        "runtime": "python3.12", "handler": "handler.lambda_handler",
                        "memory_size": 128, "timeout": 3
                    }}
                ]
            }
        }
    }
    live_config = {"Runtime": "python3.12", "Handler": "handler.lambda_handler",
                   "MemorySize": 128, "Timeout": 3}
    with patch("drift_detector.run_cmd") as mock_cmd:
        mock_cmd.side_effect = [json.dumps(tf_state), json.dumps(live_config)]
        with patch("drift_detector.client"):
            report = detect_lambda_drift("my-fn", "terraform/aws")
            assert report.has_drift is False
            assert report.diffs == []


def test_detect_lambda_drift_memory_drift():
    tf_state = {
        "values": {"root_module": {"resources": [
            {"type": "aws_lambda_function", "name": "hello", "values": {
                "runtime": "python3.12", "handler": "handler.lambda_handler",
                "memory_size": 128, "timeout": 3
            }}
        ]}}
    }
    live_config = {"Runtime": "python3.12", "Handler": "handler.lambda_handler",
                   "MemorySize": 256, "Timeout": 3}
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Memory drifted from 128 to 256."
    with patch("drift_detector.run_cmd") as mock_cmd:
        mock_cmd.side_effect = [json.dumps(tf_state), json.dumps(live_config)]
        with patch("drift_detector.client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_response
            report = detect_lambda_drift("my-fn", "terraform/aws")
            assert report.has_drift is True
            assert any("Memory" in d for d in report.diffs)


def test_detect_lambda_drift_not_in_state():
    tf_state = {"values": {"root_module": {"resources": []}}}
    with patch("drift_detector.run_cmd") as mock_cmd:
        mock_cmd.side_effect = [json.dumps(tf_state)]
        report = detect_lambda_drift("missing-fn", "terraform/aws")
        assert report.has_drift is False
        assert "not found" in report.diffs[0].lower()


def test_detect_s3_drift_no_drift():
    tf_state = {
        "values": {"root_module": {"resources": [
            {"type": "aws_s3_bucket", "name": "site", "values": {
                "tags": {"owner": "jash", "project": "pSiddhi"}
            }}
        ]}}
    }
    live_tags = {"TagSet": [{"Key": "owner", "Value": "jash"}, {"Key": "project", "Value": "pSiddhi"}]}
    with patch("drift_detector.run_cmd") as mock_cmd:
        mock_cmd.side_effect = [json.dumps(tf_state), json.dumps(live_tags), ""]
        with patch("drift_detector.client"):
            report = detect_s3_drift("my-bucket", "terraform/aws")
            assert report.has_drift is False


def test_detect_s3_drift_tag_drift():
    tf_state = {
        "values": {"root_module": {"resources": [
            {"type": "aws_s3_bucket", "name": "site", "values": {
                "tags": {"owner": "jash", "project": "pSiddhi"}
            }}
        ]}}
    }
    live_tags = {"TagSet": [{"Key": "owner", "Value": "someone-else"}]}
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Tags drifted."
    with patch("drift_detector.run_cmd") as mock_cmd:
        mock_cmd.side_effect = [json.dumps(tf_state), json.dumps(live_tags), ""]
        with patch("drift_detector.client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_response
            report = detect_s3_drift("my-bucket", "terraform/aws")
            assert report.has_drift is True
            assert any("Tags" in d for d in report.diffs)


def test_detect_storage_drift_no_drift():
    tf_state = {
        "values": {"root_module": {"resources": [
            {"type": "azurerm_storage_account", "name": "site", "values": {
                "account_tier": "Standard", "account_replication_type": "LRS",
                "https_traffic_only_enabled": True,
                "tags": {"owner": "jash"}
            }}
        ]}}
    }
    live = {
        "sku": {"tier": "Standard", "name": "Standard_LRS"},
        "properties": {"supportsHttpsTrafficOnly": True},
        "tags": {"owner": "jash"}
    }
    with patch("drift_detector.run_cmd") as mock_cmd:
        mock_cmd.side_effect = [json.dumps(tf_state), json.dumps(live)]
        with patch("drift_detector.client"):
            report = detect_storage_drift("my-acct", "terraform/azure")
            assert report.has_drift is False


def test_detect_storage_drift_replication_drift():
    tf_state = {
        "values": {"root_module": {"resources": [
            {"type": "azurerm_storage_account", "name": "site", "values": {
                "account_tier": "Standard", "account_replication_type": "LRS",
                "https_traffic_only_enabled": True, "tags": {}
            }}
        ]}}
    }
    live = {
        "sku": {"tier": "Standard", "name": "Standard_GRS"},
        "properties": {"supportsHttpsTrafficOnly": True}, "tags": {}
    }
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Replication upgraded."
    with patch("drift_detector.run_cmd") as mock_cmd:
        mock_cmd.side_effect = [json.dumps(tf_state), json.dumps(live)]
        with patch("drift_detector.client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_response
            report = detect_storage_drift("my-acct", "terraform/azure")
            assert report.has_drift is True
            assert any("Replication" in d for d in report.diffs)


def test_detect_storage_drift_not_in_state():
    tf_state = {"values": {"root_module": {"resources": []}}}
    with patch("drift_detector.run_cmd") as mock_cmd:
        mock_cmd.side_effect = [json.dumps(tf_state)]
        report = detect_storage_drift("missing", "terraform/azure")
        assert report.has_drift is False


def test_run_cmd_success():
    result = run_cmd("echo hello")
    assert "hello" in result


def test_run_cmd_failure_raises():
    try:
        run_cmd("this-command-does-not-exist-xyz-123")
        assert False, "Should have raised"
    except RuntimeError:
        pass


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
