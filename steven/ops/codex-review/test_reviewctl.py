import contextlib
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reviewctl


class DefinitionTests(unittest.TestCase):
    def setUp(self):
        self.queue = {"id": 9, "name": "Azure Pipelines"}

    def test_definition_matches_fixture(self):
        definition = reviewctl.build_definition(reviewctl.DESIRED, self.queue, False)
        fixture = json.loads((HERE / "fixtures" / "definition-shape.json").read_text())
        phase = definition["process"]["phases"][0]
        actual = {
            "identity": {key: definition[key] for key in fixture["identity"]},
            "repository": definition["repository"],
            "process": {
                "type": definition["process"]["type"],
                "image": definition["process"]["target"]["agentSpecification"]["identifier"],
                "authorizationScope": phase["jobAuthorizationScope"],
                "oauthEnabled": phase["target"]["allowScriptsAuthAccessOption"],
                "tasks": [
                    {
                        "name": task["displayName"],
                        "taskId": task["task"]["id"],
                        "version": task["task"]["versionSpec"],
                        "environment": sorted(task["environment"]),
                        "alwaysRun": task["alwaysRun"],
                    }
                    for task in phase["steps"]
                ],
            },
            "queue": definition["queue"],
        }
        self.assertEqual(fixture, actual)

    def test_policy_is_automatic_advisory_and_source_update_queued(self):
        policy = reviewctl.build_policy(reviewctl.DESIRED, 31, True)
        self.assertTrue(policy["isEnabled"])
        self.assertFalse(policy["isBlocking"])
        self.assertFalse(policy["settings"]["manualQueueOnly"])
        self.assertTrue(policy["settings"]["queueOnSourceUpdateOnly"])
        self.assertEqual("be68a2ca-fba3-4202-989e-e8f00003e11e", policy["settings"]["scope"][0]["repositoryId"])
        self.assertEqual("refs/heads/main", policy["settings"]["scope"][0]["refName"])

    def test_server_tasks_do_not_load_reviewed_repository_control_files(self):
        definition = reviewctl.build_definition(reviewctl.DESIRED, self.queue, True)
        tasks = definition["process"]["phases"][0]["steps"]
        admission, codex, publisher = tasks
        self.assertEqual({"SYSTEM_ACCESSTOKEN"}, set(admission["environment"]))
        self.assertEqual({"CODEX_API_KEY"}, set(codex["environment"]))
        self.assertEqual({"SYSTEM_ACCESSTOKEN"}, set(publisher["environment"]))
        self.assertIn("--unset-all", admission["inputs"]["script"])
        self.assertIn("extraheader", admission["inputs"]["script"])
        self.assertIn("@openai/codex@0.154.0", codex["inputs"]["script"])
        self.assertIn('--model "gpt-5.6-sol"', codex["inputs"]["script"])
        self.assertIn('model_reasoning_effort = "low"', codex["inputs"]["script"])
        self.assertIn('inherit = "core"', codex["inputs"]["script"])
        self.assertIn('"*KEY*" = "exclude"', codex["inputs"]["script"])
        self.assertIn("--no-ext-diff --no-textconv", codex["inputs"]["script"])
        self.assertIn('cd "$REVIEW_DIR"', codex["inputs"]["script"])
        self.assertIn("--skip-git-repo-check", codex["inputs"]["script"])
        self.assertIn("--ephemeral", codex["inputs"]["script"])
        self.assertIn("authenticatedUser", admission["inputs"]["script"])
        self.assertIn('comment.get("author", {}).get("id"', admission["inputs"]["script"])
        self.assertIn('comment.get("author", {}).get("id"', publisher["inputs"]["script"])
        self.assertNotIn("npm run", "\n".join(task["inputs"]["script"] for task in tasks))


class MarkerAndPlanTests(unittest.TestCase):
    def test_marker_is_deterministic_and_commit_specific(self):
        first = reviewctl.ReviewKey(reviewctl.DESIRED.repository_id, 17, "a" * 40)
        same = reviewctl.ReviewKey(reviewctl.DESIRED.repository_id.upper(), 17, "A" * 40)
        changed = reviewctl.ReviewKey(reviewctl.DESIRED.repository_id, 17, "b" * 40)
        self.assertEqual(first.marker, same.marker)
        self.assertNotEqual(first.marker, changed.marker)
        self.assertRegex(first.marker, r"^<!-- codex-review:[0-9a-f]{24} -->$")

    def test_converged_state_has_no_actions(self):
        definition = reviewctl.build_definition(reviewctl.DESIRED, {"id": 9, "name": "Azure Pipelines"}, True)
        definition.update({"id": 31, "revision": 4, "url": "ignored"})
        policy = reviewctl.build_policy(reviewctl.DESIRED, 31, True)
        policy.update({"id": 7, "revision": 2})
        remote = reviewctl.AzureState(queue={"id": 9, "name": "Azure Pipelines"}, definition=definition, policy=policy, disable_classic_build_pipeline_creation=False)
        self.assertEqual([], reviewctl.plan_actions(reviewctl.DESIRED, remote))

    def test_missing_key_blocks_policy(self):
        definition = reviewctl.build_definition(reviewctl.DESIRED, {"id": 9, "name": "Azure Pipelines"}, False)
        definition.update({"id": 31, "revision": 4})
        remote = reviewctl.AzureState(queue={"id": 9, "name": "Azure Pipelines"}, definition=definition, policy=None, disable_classic_build_pipeline_creation=False)
        actions = reviewctl.plan_actions(reviewctl.DESIRED, remote)
        self.assertIn({"action": "blocked", "resource": "build-policy", "reason": "CODEX_API_KEY is missing"}, actions)
        self.assertIn({"action": "set-key", "resource": "pipeline-secret", "name": "CODEX_API_KEY"}, actions)

    def test_managed_policy_requires_matching_repository_and_branch(self):
        matching = reviewctl.build_policy(reviewctl.DESIRED, 31, True)
        other_repo = reviewctl.build_policy(reviewctl.DESIRED, 31, True)
        other_repo["settings"]["scope"][0]["repositoryId"] = "00000000-0000-0000-0000-000000000000"
        other_branch = reviewctl.build_policy(reviewctl.DESIRED, 31, True)
        other_branch["settings"]["scope"][0]["refName"] = "refs/heads/release"
        self.assertTrue(reviewctl._is_managed_policy(matching, reviewctl.DESIRED))
        self.assertFalse(reviewctl._is_managed_policy(other_repo, reviewctl.DESIRED))
        self.assertFalse(reviewctl._is_managed_policy(other_branch, reviewctl.DESIRED))


class AzureSettingsTests(unittest.TestCase):
    def setUp(self):
        self.desired = reviewctl.build_definition(reviewctl.DESIRED, {"id": 9, "name": "Azure Pipelines"}, False)

    def make_client(self, invoke):
        client = reviewctl.AzureCli(reviewctl.DESIRED)
        client._invoke = mock.Mock(side_effect=invoke)
        return client

    def test_initial_post_temporarily_enables_creation_and_restores_true(self):
        disabled = True
        calls = []

        def invoke(area, resource, method="GET", **kwargs):
            nonlocal disabled
            calls.append((resource, method, kwargs.get("body")))
            if resource == "generalSettings" and method == "GET":
                return {"disableClassicBuildPipelineCreation": disabled}
            if resource == "generalSettings" and method == "PATCH":
                disabled = kwargs["body"]["disableClassicBuildPipelineCreation"]
                return {}
            if resource == "definitions" and method == "POST":
                self.assertFalse(disabled)
                return {"id": 31}
            self.fail((resource, method))

        result = self.make_client(invoke).save_definition(self.desired, None)
        self.assertEqual(31, result["id"])
        self.assertTrue(disabled)
        self.assertEqual(
            [
                ("generalSettings", "GET", None),
                ("generalSettings", "PATCH", {"disableClassicBuildPipelineCreation": False}),
                ("generalSettings", "GET", None),
                ("definitions", "POST", self.desired),
                ("generalSettings", "PATCH", {"disableClassicBuildPipelineCreation": True}),
                ("generalSettings", "GET", None),
            ],
            calls,
        )

    def test_initial_post_does_not_write_when_creation_is_already_enabled(self):
        calls = []

        def invoke(area, resource, method="GET", **kwargs):
            calls.append((resource, method))
            if resource == "generalSettings":
                return {"disableClassicBuildPipelineCreation": False}
            if resource == "definitions" and method == "POST":
                return {"id": 31}
            self.fail((resource, method))

        self.make_client(invoke).save_definition(self.desired, None)
        self.assertEqual([("generalSettings", "GET"), ("definitions", "POST")], calls)

    def test_existing_definition_put_never_reads_or_writes_general_settings(self):
        calls = []

        def invoke(area, resource, method="GET", **kwargs):
            calls.append((resource, method, kwargs.get("body")))
            if resource == "definitions" and method == "PUT":
                return {"id": 31}
            self.fail((resource, method))

        self.make_client(invoke).save_definition(self.desired, {"id": 31, "revision": 4})
        self.assertEqual("definitions", calls[0][0])
        self.assertEqual("PUT", calls[0][1])
        self.assertEqual(1, len(calls))

    def test_post_failure_restores_original_true_value(self):
        disabled = True

        def invoke(area, resource, method="GET", **kwargs):
            nonlocal disabled
            if resource == "generalSettings" and method == "GET":
                return {"disableClassicBuildPipelineCreation": disabled}
            if resource == "generalSettings" and method == "PATCH":
                disabled = kwargs["body"]["disableClassicBuildPipelineCreation"]
                return {}
            raise reviewctl.BoundaryError("definition post failed")

        with self.assertRaisesRegex(reviewctl.BoundaryError, "definition post failed"):
            self.make_client(invoke).save_definition(self.desired, None)
        self.assertTrue(disabled)

    def test_enable_failure_still_restores_original_true_value(self):
        disabled = True
        patches = []

        def invoke(area, resource, method="GET", **kwargs):
            nonlocal disabled
            if resource == "generalSettings" and method == "GET":
                return {"disableClassicBuildPipelineCreation": disabled}
            if resource == "generalSettings" and method == "PATCH":
                value = kwargs["body"]["disableClassicBuildPipelineCreation"]
                patches.append(value)
                if value is False:
                    raise reviewctl.BoundaryError("enable denied")
                disabled = value
                return {}
            self.fail((resource, method))

        with self.assertRaisesRegex(reviewctl.BoundaryError, "enable denied"):
            self.make_client(invoke).save_definition(self.desired, None)
        self.assertEqual([False, True], patches)
        self.assertTrue(disabled)

    def test_restoration_failure_stops_apply_before_policy_changes(self):
        disabled = True
        policy_calls = []

        class Client(reviewctl.AzureCli):
            def read_state(inner_self):
                return reviewctl.AzureState(
                    queue={"id": 9, "name": "Azure Pipelines"},
                    definition=None,
                    policy=None,
                    disable_classic_build_pipeline_creation=True,
                )

            def save_policy(inner_self, desired, existing):
                policy_calls.append((desired, existing))
                return {"id": 7}

        client = Client(reviewctl.DESIRED)

        def invoke(area, resource, method="GET", **kwargs):
            nonlocal disabled
            if resource == "generalSettings" and method == "GET":
                return {"disableClassicBuildPipelineCreation": disabled}
            if resource == "generalSettings" and method == "PATCH":
                value = kwargs["body"]["disableClassicBuildPipelineCreation"]
                if value is True:
                    raise reviewctl.BoundaryError("restore denied")
                disabled = value
                return {}
            if resource == "definitions" and method == "POST":
                return {"id": 31}
            self.fail((resource, method))

        client._invoke = mock.Mock(side_effect=invoke)
        with self.assertRaisesRegex(reviewctl.BoundaryError, "restore denied"):
            reviewctl.command_apply(client)
        self.assertEqual([], policy_calls)

    def test_post_and_restoration_failures_are_both_reported(self):
        disabled = True

        def invoke(area, resource, method="GET", **kwargs):
            nonlocal disabled
            if resource == "generalSettings" and method == "GET":
                return {"disableClassicBuildPipelineCreation": disabled}
            if resource == "generalSettings" and method == "PATCH":
                value = kwargs["body"]["disableClassicBuildPipelineCreation"]
                if value is True:
                    raise reviewctl.BoundaryError("restore denied")
                disabled = value
                return {}
            raise reviewctl.BoundaryError("definition post failed")

        with self.assertRaises(reviewctl.BoundaryError) as raised:
            self.make_client(invoke).save_definition(self.desired, None)
        self.assertIn("definition post failed", str(raised.exception))
        self.assertIn("restore denied", str(raised.exception))

    def test_nonboolean_setting_is_rejected(self):
        for value in (None, 0, 1, "true", {}, []):
            with self.subTest(value=value):
                client = self.make_client(lambda *args, **kwargs: {"disableClassicBuildPipelineCreation": value})
                with self.assertRaisesRegex(reviewctl.BoundaryError, "invalid disableClassicBuildPipelineCreation"):
                    client.get_classic_build_pipeline_creation_disabled()


class ProjectSettingCommandTests(unittest.TestCase):
    def state(self, disabled):
        definition = reviewctl.build_definition(reviewctl.DESIRED, {"id": 9, "name": "Azure Pipelines"}, True)
        definition.update({"id": 31, "revision": 4})
        policy = reviewctl.build_policy(reviewctl.DESIRED, 31, True)
        policy["id"] = 7
        return reviewctl.AzureState(
            queue={"id": 9, "name": "Azure Pipelines"},
            definition=definition,
            policy=policy,
            disable_classic_build_pipeline_creation=disabled,
        )

    def test_plan_reports_redacted_temporary_update_only_for_missing_definition(self):
        for disabled, expected in ((True, 1), (False, 0)):
            with self.subTest(disabled=disabled):
                remote = reviewctl.AzureState(
                    queue={"id": 9, "name": "Azure Pipelines"},
                    definition=None,
                    policy=None,
                    disable_classic_build_pipeline_creation=disabled,
                )
                client = mock.Mock()
                client.read_state.return_value = remote
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(0, reviewctl.command_plan(client))
                actions = json.loads(output.getvalue())["actions"]
                temporary = [action for action in actions if action["action"] == "temporarily-update"]
                self.assertEqual(expected, len(temporary))
                if temporary:
                    self.assertEqual("***", temporary[0]["value"])
                self.assertEqual([mock.call.read_state()], client.mock_calls)
        existing_actions = reviewctl.plan_actions(reviewctl.DESIRED, self.state(True))
        self.assertFalse(any(action["action"] == "temporarily-update" for action in existing_actions))

    def test_verify_accepts_either_setting_without_mutating_it(self):
        for disabled in (True, False):
            with self.subTest(disabled=disabled):
                client = mock.Mock()
                client.read_state.return_value = self.state(disabled)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    result = reviewctl.command_verify(client)
                self.assertEqual(0, result)
                self.assertTrue(json.loads(output.getvalue())["verified"])
                client.read_state.assert_called_once_with()
                self.assertEqual([mock.call.read_state()], client.mock_calls)


class SecretTests(unittest.TestCase):
    def test_set_key_uses_environment_not_argv(self):
        captured = {}

        class Client(reviewctl.AzureCli):
            def _run(self, args, *, env=None):
                captured["args"] = args
                captured["env"] = env

        Client(reviewctl.DESIRED).set_key(31, "never-in-argv", True)
        self.assertNotIn("never-in-argv", captured["args"])
        self.assertEqual("never-in-argv", captured["env"]["AZURE_DEVOPS_EXT_PIPELINE_VAR_CODEX_API_KEY"])
        self.assertNotIn("CODEX_API_KEY", captured["env"])
        self.assertIn("--prompt-value", captured["args"])

    def test_redaction_recurses(self):
        value = {
            "authorizationToken": "token-value",
            "variables": {"CODEX_API_KEY": {"value": "secret-value", "isSecret": True}},
            "safe": "visible",
        }
        redacted = reviewctl.redact(value)
        self.assertEqual("***", redacted["authorizationToken"])
        self.assertEqual("***", redacted["variables"]["CODEX_API_KEY"]["value"])
        self.assertEqual("visible", redacted["safe"])
        self.assertNotIn("secret-value", json.dumps(redacted))

    def test_secret_reads_environment_or_stdin(self):
        self.assertEqual("from-env", reviewctl.read_secret(io.StringIO("ignored"), {"CODEX_API_KEY": "from-env"}))
        self.assertEqual("from-stdin", reviewctl.read_secret(io.StringIO("from-stdin\n"), {}))
        with self.assertRaises(reviewctl.BoundaryError):
            reviewctl.read_secret(io.StringIO("\n"), {})


class CommandValidationTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(HERE / "reviewctl.py"), *args],
            input="",
            text=True,
            capture_output=True,
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )

    def test_rejects_unknown_command(self):
        result = self.run_cli("destroy")
        self.assertEqual(2, result.returncode)
        self.assertIn("invalid choice", result.stderr)

    def test_set_key_rejects_argv_value(self):
        result = self.run_cli("set-key", "super-secret")
        self.assertEqual(2, result.returncode)
        self.assertIn("unrecognized arguments", result.stderr)
        self.assertNotIn("super-secret", result.stdout)


if __name__ == "__main__":
    unittest.main()
