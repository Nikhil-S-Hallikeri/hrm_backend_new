from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class WorkflowStep(BaseModel):
    id: str
    name: str
    required_slot: str | None = None
    prompt_question: str | None = None


class WorkflowDefinition(BaseModel):
    id: str
    name: str
    steps: list[WorkflowStep] = Field(default_factory=list)


class InterruptedWorkflow(BaseModel):
    workflow_id: str
    step_id: str
    collected_slots: dict[str, Any] = Field(default_factory=dict)
    reason: str = "user_topic_switch"


class StateContext(BaseModel):
    active_intent: str | None = None
    current_workflow_id: str | None = None
    current_step_id: str | None = None
    workflow_stack: list[InterruptedWorkflow] = Field(default_factory=list)
    collected_slots: dict[str, Any] = Field(default_factory=dict)
    user_facts: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""

    def push_interrupted_workflow(self, reason: str = "user_topic_switch") -> None:
        if self.current_workflow_id and self.current_step_id:
            self.workflow_stack.append(
                InterruptedWorkflow(
                    workflow_id=self.current_workflow_id,
                    step_id=self.current_step_id,
                    collected_slots=dict(self.collected_slots),
                    reason=reason,
                )
            )

    def pop_interrupted_workflow(self) -> InterruptedWorkflow | None:
        if self.workflow_stack:
            interrupted = self.workflow_stack.pop()
            self.current_workflow_id = interrupted.workflow_id
            self.current_step_id = interrupted.step_id
            return interrupted
        return None

    def update_slots(self, new_slots: dict[str, Any]) -> None:
        for k, v in new_slots.items():
            if v is not None and v != "":
                self.collected_slots[k] = v


BUILTIN_WORKFLOWS: dict[str, WorkflowDefinition] = {
    "lead_capture": WorkflowDefinition(
        id="lead_capture",
        name="Lead Qualification & Contact Capture",
        steps=[
            WorkflowStep(id="collect_name", name="Collect Name", required_slot="name", prompt_question="May I know your name?"),
            WorkflowStep(id="collect_contact", name="Collect Email or Phone", required_slot="phone", prompt_question="What is your phone number or email address?"),
            WorkflowStep(id="collect_interest", name="Identify Requirement", required_slot="interest", prompt_question="How can our services help your business today?"),
        ],
    ),
    "job_application": WorkflowDefinition(
        id="job_application",
        name="Job Application Flow",
        steps=[
            WorkflowStep(id="collect_role", name="Desired Role", required_slot="role", prompt_question="Which position or role are you applying for?"),
            WorkflowStep(id="collect_experience", name="Experience Level", required_slot="experience", prompt_question="How many years of experience do you have in this field?"),
            WorkflowStep(id="collect_contact", name="Contact Phone", required_slot="phone", prompt_question="Please provide a phone number where our HR team can reach you."),
        ],
    ),
}
