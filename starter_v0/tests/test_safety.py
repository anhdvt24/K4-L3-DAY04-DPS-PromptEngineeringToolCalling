"""Offline regression tests; fake providers here are not lab run evidence."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from agent import HelpdeskAgent
from chat import execute_tool_call, run_model_tool_loop, write_transcript
from providers.base import ModelResponse, ToolCall
from safety import REDACTED, REFUSAL, is_sensitive, redact, safe_messages


class SafetyTests(unittest.TestCase):
    def test_sensitive_formats_and_public_questions(self):
        for value in ["4111 1111 1111 1111", "OTP=123456", "CVV: 123",
                      "password=SummerExample!", "mật khẩu=Example!", "api_key=example"]:
            with self.subTest(value=value):
                self.assertTrue(is_sensitive(value))
        for value in ["Có nên gửi OTP không?", "chính sách thanh toán", "TOUR-DL01 2026-10-20 KH-1001"]:
            self.assertFalse(is_sensitive(value))

    def test_eval_refuses_before_provider(self):
        provider = Mock()
        agent = HelpdeskAgent(provider, system_prompt="test")
        result = agent.run([{"role": "user", "content": "Đặt tour, CVV=123, tôi xác nhận"}])
        provider.complete.assert_not_called()
        self.assertEqual(result.text, REFUSAL)
        self.assertEqual(result.tool_calls, [])
        self.assertEqual(result.safety_guard, "sensitive_input")

    def test_chat_refuses_before_provider_and_tools(self):
        provider = Mock()
        result = run_model_tool_loop(provider=provider,
            messages=[{"role": "user", "content": "4111 1111 1111 1111"}],
            tools=[], model=None, max_tool_rounds=4)
        provider.complete.assert_not_called()
        self.assertEqual(result["tool_events"], [])
        self.assertEqual(result["rounds"], [])

    def test_public_request_still_calls_provider(self):
        provider = Mock()
        provider.complete.return_value = ModelResponse(text="public answer")
        agent = HelpdeskAgent(provider, system_prompt="test")
        self.assertEqual(agent.run([{"role": "user", "content": "Chính sách thanh toán?"}]).text, "public answer")
        provider.complete.assert_called_once()

    def test_model_cannot_send_secret_to_tool_in_chat(self):
        tool = Mock()
        with patch.dict("chat.TOOL_FUNCTIONS", {"create_booking": tool}):
            event = execute_tool_call(ToolCall("create_booking", {"note": "CVV=123", "confirmed": True}))
        tool.assert_not_called()
        self.assertEqual(event["result"]["error"], "restricted_sensitive_data")
        self.assertNotIn("123", json.dumps(event))

    def test_model_cannot_send_secret_to_tool_in_eval(self):
        tool = Mock()
        provider = Mock()
        provider.complete.return_value = ModelResponse(tool_calls=[ToolCall("create_booking", {"note": "password=example!"})])
        with patch.dict("agent.TOOL_FUNCTIONS", {"create_booking": tool}):
            result = HelpdeskAgent(provider, system_prompt="test").run([{"role": "user", "content": "Đặt tour"}])
        tool.assert_not_called()
        self.assertEqual(result.tool_results[0]["result"]["error"], "restricted_sensitive_data")

    def test_redaction_is_recursive_and_non_mutating(self):
        source = {"turns": [{"user": "OTP=123456", "tool_results": [{"note": "CVV=123"}]}]}
        cleaned = redact(source)
        self.assertNotIn("123", json.dumps(cleaned))
        self.assertEqual(source["turns"][0]["user"], "OTP=123456")

    def test_persisted_transcript_is_redacted(self):
        with TemporaryDirectory(prefix="travel-safety-") as directory:
            path = Path(directory) / "unit-test.json"
            write_transcript(path, {"user": "CVV=123"})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["user"], REDACTED)

    def test_old_sensitive_history_is_not_forwarded(self):
        messages = [{"role": "user", "content": "OTP=123456"}, {"role": "user", "content": "Xin chào"}]
        self.assertEqual(safe_messages(messages)[0]["content"], REDACTED)
        self.assertEqual(messages[0]["content"], "OTP=123456")

    def test_blocked_arguments_are_not_forwarded_in_next_round(self):
        provider = Mock()
        provider.complete.side_effect = [
            ModelResponse(tool_calls=[ToolCall("create_booking", {"note": "CVV=123"})]),
            ModelResponse(text="CVV=123"),
        ]
        result = run_model_tool_loop(provider=provider,
            messages=[{"role": "user", "content": "Đặt tour"}], tools=[], model=None, max_tool_rounds=2)
        self.assertNotIn("CVV=123", json.dumps(provider.complete.call_args_list[1].args[0]))
        self.assertEqual(result["assistant_text"], REDACTED)


if __name__ == "__main__":
    unittest.main()
