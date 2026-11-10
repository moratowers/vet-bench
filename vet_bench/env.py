"""The environment: one agent per episode, with a harness chosen from the task's tools.

Unless the user picks a harness (`--env.agent.harness.id`), the agent gets:
  - `null` in read mode and in the macOS shell mode: a plain chat loop with no shell or
    file tools of its own, so the only tools are the ones the task adds;
  - `bash` in the container shell mode: verifiers' own harness, whose bash and edit tools
    run inside the rollout's container (see vet_bench/container.py).
This is the pattern verifiers' docs/env.md describes for a role whose default harness
depends on a taskset setting: type the env's `taskset` field with the taskset's config and
choose the harness in an `after` validator, only when the user left it unset.
"""

from pydantic import model_validator

import verifiers.v1 as vf
from vet_bench.taskset import VetTasksetConfig


def default_harness(taskset: VetTasksetConfig) -> str:
    """The harness id the agent gets when none was chosen."""
    return "bash" if taskset.task.mode == "container" else "null"


class VetEnvConfig(vf.EnvConfig):
    taskset: VetTasksetConfig = VetTasksetConfig()
    agent: vf.AgentConfig = vf.AgentConfig()

    @model_validator(mode="after")
    def _pick_harness(self) -> "VetEnvConfig":
        if self.agent.harness is None:
            harness = {"id": default_harness(self.taskset)}
            self.agent = vf.AgentConfig.model_validate({**self.agent.model_dump(), "harness": harness})
        return self


class VetEnv(vf.Env[VetEnvConfig]):
    async def run(self, task: vf.Task, agents: vf.Agents) -> None:
        await agents.agent.run(task)
