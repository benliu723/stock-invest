import argparse
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "stock_pools.py"


def load_module():
    spec = importlib.util.spec_from_file_location("stock_pools_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class StockPoolsTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.state_path = Path(self.tempdir.name) / "stock_pools.json"
        self.module.STATE_PATH = self.state_path
        self.module._AKSHARE_CODE_NAME_MAP = None

    def tearDown(self):
        self.tempdir.cleanup()

    def run_json_command(self, func, args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            func(args)
        return json.loads(buf.getvalue())

    def read_state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def test_follow_stock_saves_ticker_id(self):
        with patch.object(self.module, "lookup_ticker_id", return_value="300827"):
            result = self.run_json_command(
                self.module.follow_stock,
                argparse.Namespace(stock_name="上能电气", pools=None),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["ticker_id"], "300827")
        state = self.read_state()
        self.assertEqual(state["pools"]["默认股票池"]["members"], ["300827"])

    def test_show_all_stocks_normalizes_legacy_name_members(self):
        legacy_state = {
            "pools": {
                "默认股票池": {
                    "name": "默认股票池",
                    "is_default": True,
                    "members": ["上能电气"],
                }
            }
        }
        self.state_path.write_text(
            json.dumps(legacy_state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        with patch.object(self.module, "lookup_ticker_id", return_value="300827"):
            result = self.run_json_command(
                self.module.show_all_stocks,
                argparse.Namespace(),
            )

        self.assertEqual(result["pools"]["默认股票池"], ["300827"])
        self.assertEqual(result["all_stocks"], ["300827"])
        state = self.read_state()
        self.assertEqual(state["pools"]["默认股票池"]["members"], ["300827"])

    def test_add_stock_command_saves_ticker_id(self):
        self.module.save_state(self.module.default_state())

        with patch.object(self.module, "lookup_ticker_id", return_value="300827"):
            result = self.run_json_command(
                self.module.add_stock,
                argparse.Namespace(pool_name="默认股票池", stock_name="上能电气"),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["tickid"], "300827")
        self.assertEqual(result["stock_name"], "上能电气")
        state = self.read_state()
        self.assertEqual(state["pools"]["默认股票池"]["members"], ["300827"])

    def test_text_command_follow_saves_ticker_id(self):
        with patch.object(self.module, "lookup_ticker_id", return_value="300827"):
            result = self.run_json_command(
                self.module.text_command,
                argparse.Namespace(text="关注 上能电气", pools=None),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["ticker_id"], "300827")
        state = self.read_state()
        self.assertEqual(state["pools"]["默认股票池"]["members"], ["300827"])

    def test_unfollow_stock_by_name_removes_saved_ticker_id(self):
        self.module.save_state(
            {
                "pools": {
                    "默认股票池": {
                        "name": "默认股票池",
                        "is_default": True,
                        "members": ["300827"],
                    }
                }
            }
        )

        with patch.object(self.module, "lookup_ticker_id", return_value="300827"):
            result = self.run_json_command(
                self.module.unfollow_stock,
                argparse.Namespace(stock_name="上能电气", pools=["默认股票池"]),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["ticker_id"], "300827")
        state = self.read_state()
        self.assertEqual(state["pools"]["默认股票池"]["members"], [])

    def test_text_command_create_pool_with_stock_pool_phrase(self):
        result = self.run_json_command(
            self.module.text_command,
            argparse.Namespace(text="新建一个叫储能的股票池", pools=None),
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["pool_name"], "储能")
        state = self.read_state()
        self.assertIn("储能", state["pools"])

    def test_text_command_add_stock_with_stock_pool_phrase(self):
        self.module.create_pool_impl("储能")

        with patch.object(self.module, "lookup_ticker_id", return_value="300827"):
            result = self.run_json_command(
                self.module.text_command,
                argparse.Namespace(text="将上能电气加入储能股票池中", pools=None),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["tickid"], "300827")
        state = self.read_state()
        self.assertEqual(state["pools"]["储能"]["members"], ["300827"])

    def test_text_command_remove_stock_with_stock_pool_phrase(self):
        self.module.save_state(
            {
                "pools": {
                    "默认股票池": {
                        "name": "默认股票池",
                        "is_default": True,
                        "members": [],
                    },
                    "储能": {
                        "name": "储能",
                        "is_default": False,
                        "members": ["300827"],
                    },
                }
            }
        )

        with patch.object(self.module, "lookup_ticker_id", return_value="300827"):
            result = self.run_json_command(
                self.module.text_command,
                argparse.Namespace(text="把上能电气从储能池删掉", pools=None),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["tickid"], "300827")
        state = self.read_state()
        self.assertEqual(state["pools"]["储能"]["members"], [])

    def test_text_command_follow_auto_creates_missing_pool(self):
        with patch.object(self.module, "lookup_ticker_id", return_value="300827"):
            result = self.run_json_command(
                self.module.text_command,
                argparse.Namespace(text="关注 上能电气到默认股票池和储能池", pools=None),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["selected_pools"], ["默认股票池", "储能"])
        self.assertEqual(result["created_pools"], ["储能"])
        state = self.read_state()
        self.assertEqual(state["pools"]["默认股票池"]["members"], ["300827"])
        self.assertEqual(state["pools"]["储能"]["members"], ["300827"])

    def test_text_command_follow_auto_creates_missing_pool_with_sentence_punctuation(self):
        with patch.object(self.module, "lookup_ticker_id", return_value="300827"):
            result = self.run_json_command(
                self.module.text_command,
                argparse.Namespace(text="关注 上能电气到默认股票池和储能池。", pools=None),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["selected_pools"], ["默认股票池", "储能"])
        self.assertEqual(result["created_pools"], ["储能"])

    def test_text_command_unfollow_with_pool_aliases(self):
        self.module.save_state(
            {
                "pools": {
                    "默认股票池": {
                        "name": "默认股票池",
                        "is_default": True,
                        "members": ["300827"],
                    },
                    "储能": {
                        "name": "储能",
                        "is_default": False,
                        "members": ["300827"],
                    },
                }
            }
        )

        with patch.object(self.module, "lookup_ticker_id", return_value="300827"):
            result = self.run_json_command(
                self.module.text_command,
                argparse.Namespace(text="从默认池和储能池取消关注上能电气", pools=None),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["selected_pools"], ["默认股票池", "储能"])
        state = self.read_state()
        self.assertEqual(state["pools"]["默认股票池"]["members"], [])
        self.assertEqual(state["pools"]["储能"]["members"], [])

    def test_text_command_rename_and_show_with_stock_pool_phrases(self):
        self.module.save_state(
            {
                "pools": {
                    "默认股票池": {
                        "name": "默认股票池",
                        "is_default": True,
                        "members": [],
                    },
                    "储能": {
                        "name": "储能",
                        "is_default": False,
                        "members": ["300827"],
                    },
                }
            }
        )

        rename_result = self.run_json_command(
            self.module.text_command,
            argparse.Namespace(text="股票池 储能修改为储能-2", pools=None),
        )
        show_result = self.run_json_command(
            self.module.text_command,
            argparse.Namespace(text="储能-2池有哪些股票？", pools=None),
        )

        self.assertTrue(rename_result["ok"])
        self.assertEqual(rename_result["new_pool_name"], "储能-2")
        self.assertTrue(show_result["ok"])
        self.assertEqual(show_result["pool_name"], "储能-2")
        self.assertEqual(show_result["pool"]["members"], ["300827"])

    def test_text_command_show_all_stocks_with_context_prefix(self):
        self.module.save_state(
            {
                "pools": {
                    "默认股票池": {
                        "name": "默认股票池",
                        "is_default": True,
                        "members": [],
                    },
                    "储能": {
                        "name": "储能",
                        "is_default": False,
                        "members": ["300827"],
                    },
                    "光伏": {
                        "name": "光伏",
                        "is_default": False,
                        "members": ["601012"],
                    },
                }
            }
        )

        result = self.run_json_command(
            self.module.text_command,
            argparse.Namespace(text="当前已经保存了储能和光伏两个股票组。获取所有组的股票。", pools=None),
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "show_all_stocks")
        self.assertEqual(result["pools"]["储能"], ["300827"])
        self.assertEqual(result["pools"]["光伏"], ["601012"])


if __name__ == "__main__":
    unittest.main()
