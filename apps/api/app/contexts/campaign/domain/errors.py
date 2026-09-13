from app.contexts.campaign.domain.lead import LeadState


class CampaignHasNoStepsError(Exception):
    pass


class NegativeStepDelayError(Exception):
    pass


class CampaignNotActiveError(Exception):
    pass


class LeadNotInCampaignError(Exception):
    pass


class LeadTransitionError(Exception):
    def __init__(self, state: LeadState, action: str) -> None:
        super().__init__(f"lead in state {state} cannot {action}")
        self.state = state
        self.action = action
