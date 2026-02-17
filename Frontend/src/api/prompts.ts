/**
 * API промптов (системные и шаблоны агентов)
 * @see API_DOCS.md v1.0.0
 */

import { apiFetch } from './client'

export interface SystemPromptsResponse {
  base: string
  single: string
  orchestration: string
}

export interface TemplatesResponse {
  templates: string[]
  descriptions: Record<string, string>
}

export interface TemplateDetailResponse {
  name: string
  template: string
}

export interface BuildPromptRequest {
  template_name: string
  name: string
  character: string
  speech_style?: string | null
  traits?: string | null
  phrases?: string | null
  universe?: string | null
  role?: string | null
  expertise?: string | null
  motivation?: string | null
  attitude?: string | null
}

export interface BuildPromptResponse {
  prompt: string
  template: string
}

/**
 * GET /api/prompts/system — системные промпты
 */
export async function fetchSystemPrompts(): Promise<SystemPromptsResponse> {
  return apiFetch<SystemPromptsResponse>('/api/prompts/system', { skipAuth: true })
}

/**
 * GET /api/prompts/templates — список шаблонов
 */
export async function fetchTemplates(): Promise<TemplatesResponse> {
  return apiFetch<TemplatesResponse>('/api/prompts/templates', { skipAuth: true })
}

/**
 * GET /api/prompts/templates/{name} — шаблон по имени
 */
export async function fetchTemplate(name: string): Promise<TemplateDetailResponse> {
  return apiFetch<TemplateDetailResponse>(`/api/prompts/templates/${encodeURIComponent(name)}`, {
    skipAuth: true,
  })
}

/**
 * POST /api/prompts/build — собрать промпт из шаблона
 */
export async function buildPrompt(data: BuildPromptRequest): Promise<BuildPromptResponse> {
  const body: Record<string, unknown> = {
    template_name: data.template_name,
    name: data.name,
    character: data.character,
  }
  if (data.speech_style != null) body.speech_style = data.speech_style
  if (data.traits != null) body.traits = data.traits
  if (data.phrases != null) body.phrases = data.phrases
  if (data.universe != null) body.universe = data.universe
  if (data.role != null) body.role = data.role
  if (data.expertise != null) body.expertise = data.expertise
  if (data.motivation != null) body.motivation = data.motivation
  if (data.attitude != null) body.attitude = data.attitude

  return apiFetch<BuildPromptResponse>('/api/prompts/build', {
    method: 'POST',
    body: JSON.stringify(body),
    skipAuth: true,
  })
}
