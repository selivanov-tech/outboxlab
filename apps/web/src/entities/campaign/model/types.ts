import type { components } from '@/shared/api/generated/api-v1';

export type CampaignSummary = components['schemas']['CampaignSummaryResponse'];
export type CampaignDetail = components['schemas']['CampaignDetailResponse'];
export type CampaignMetrics = components['schemas']['CampaignMetricsResponse'];
export type CampaignStep = components['schemas']['Step'];
export type Lead = components['schemas']['LeadResponse'];
export type NewCampaign = components['schemas']['CreateCampaignRequest'];
export type AddLeadsResult = components['schemas']['AddLeadsResponse'];
export type StartCampaignResult = components['schemas']['StartCampaignResponse'];

export const LEAD_STATES = ['pending', 'scheduled', 'sent', 'done', 'paused', 'failed'] as const;
export type LeadState = (typeof LEAD_STATES)[number];
