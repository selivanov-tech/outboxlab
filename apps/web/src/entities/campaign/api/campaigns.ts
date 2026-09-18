import 'server-only';

import { api, unwrap } from '@/shared/api/outboxlab-api';

import type {
  AddLeadsResult,
  CampaignDetail,
  CampaignMetrics,
  CampaignSummary,
  NewCampaign,
  StartCampaignResult,
} from '../model/types';

export async function getCampaigns(): Promise<CampaignSummary[]> {
  return unwrap(await (await api()).GET('/campaigns'));
}

export async function getCampaign(id: string): Promise<CampaignDetail> {
  return unwrap(
    await (await api()).GET('/campaigns/{campaign_id}', { params: { path: { campaign_id: id } } }),
  );
}

export async function getCampaignMetrics(id: string): Promise<CampaignMetrics> {
  return unwrap(
    await (
      await api()
    ).GET('/campaigns/{campaign_id}/metrics', { params: { path: { campaign_id: id } } }),
  );
}

export async function createCampaign(campaign: NewCampaign): Promise<{ id: string }> {
  return unwrap(await (await api()).POST('/campaigns', { body: campaign }));
}

export async function addLeads(id: string, emails: string[]): Promise<AddLeadsResult> {
  return unwrap(
    await (
      await api()
    ).POST('/campaigns/{campaign_id}/leads', {
      params: { path: { campaign_id: id } },
      body: { emails },
    }),
  );
}

export async function startCampaign(id: string): Promise<StartCampaignResult> {
  return unwrap(
    await (
      await api()
    ).POST('/campaigns/{campaign_id}/start', { params: { path: { campaign_id: id } } }),
  );
}
