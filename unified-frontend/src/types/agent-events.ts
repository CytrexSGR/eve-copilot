/**
 * Agent Event Types for AI Copilot
 * Defines all event types emitted by the agent during task execution
 */

export enum AgentEventType {
  // Session events
  SESSION_STARTED = 'session_started',
  SESSION_ENDED = 'session_ended',
  SESSION_ERROR = 'session_error',

  // Planning events
  PLANNING_STARTED = 'planning_started',
  PLAN_PROPOSED = 'plan_proposed',
  PLAN_APPROVED = 'plan_approved',
  PLAN_REJECTED = 'plan_rejected',
  PLAN_MODIFIED = 'plan_modified',

  // Execution events
  EXECUTION_STARTED = 'execution_started',
  EXECUTION_PAUSED = 'execution_paused',
  EXECUTION_RESUMED = 'execution_resumed',
  EXECUTION_CANCELLED = 'execution_cancelled',

  // Tool call events
  TOOL_CALL_STARTED = 'tool_call_started',
  TOOL_CALL_COMPLETED = 'tool_call_completed',
  TOOL_CALL_FAILED = 'tool_call_failed',

  // Step events
  STEP_STARTED = 'step_started',
  STEP_COMPLETED = 'step_completed',
  STEP_FAILED = 'step_failed',

  // Task events
  TASK_COMPLETED = 'task_completed',
  TASK_FAILED = 'task_failed',

  // Interaction events
  APPROVAL_REQUIRED = 'approval_required',
  CLARIFICATION_NEEDED = 'clarification_needed',

  // Streaming events
  TOKEN = 'token',
}

/**
 * Base interface for all agent events
 */
export interface AgentEvent {
  id: string;
  type: AgentEventType;
  timestamp: string;
  session_id: string;
  payload: unknown;
}

/**
 * Plan step status
 */
export type PlanStepStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';

/**
 * Individual step within a plan
 */
export interface PlanStep {
  id: string;
  description: string;
  tool: string;
  status: PlanStepStatus;
}

/**
 * Risk level for a proposed plan
 */
export type RiskLevel = 'low' | 'medium' | 'high';

/**
 * Payload for plan_proposed events
 */
export interface PlanProposedEventPayload {
  plan_id: string;
  title: string;
  description: string;
  steps: PlanStep[];
  estimated_duration: number;
  risk_level: RiskLevel;
  auto_executing: boolean;
}

/**
 * Payload for tool_call_started events
 */
export interface ToolCallStartedEventPayload {
  tool_call_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  step_id?: string;
}

/**
 * Payload for tool_call_completed events
 */
export interface ToolCallCompletedEventPayload {
  tool_call_id: string;
  tool_name: string;
  result: unknown;
  duration_ms: number;
  step_id?: string;
}

/**
 * Payload for tool_call_failed events
 */
export interface ToolCallFailedEventPayload {
  tool_call_id: string;
  tool_name: string;
  error: string;
  error_code?: string;
  step_id?: string;
}

/**
 * Payload for approval_required events
 */
export interface ApprovalRequiredEventPayload {
  approval_id: string;
  action: string;
  description: string;
  risk_level: RiskLevel;
  timeout_seconds?: number;
}

// Type Guards

/**
 * Type guard for plan_proposed events
 */
export function isPlanProposedEvent(
  event: AgentEvent
): event is AgentEvent & { payload: PlanProposedEventPayload } {
  return event.type === AgentEventType.PLAN_PROPOSED;
}

/**
 * Type guard for tool_call_started events
 */
export function isToolCallStartedEvent(
  event: AgentEvent
): event is AgentEvent & { payload: ToolCallStartedEventPayload } {
  return event.type === AgentEventType.TOOL_CALL_STARTED;
}

/**
 * Type guard for tool_call_completed events
 */
export function isToolCallCompletedEvent(
  event: AgentEvent
): event is AgentEvent & { payload: ToolCallCompletedEventPayload } {
  return event.type === AgentEventType.TOOL_CALL_COMPLETED;
}

/**
 * Type guard for tool_call_failed events
 */
export function isToolCallFailedEvent(
  event: AgentEvent
): event is AgentEvent & { payload: ToolCallFailedEventPayload } {
  return event.type === AgentEventType.TOOL_CALL_FAILED;
}

/**
 * Type guard for approval_required events
 */
export function isApprovalRequiredEvent(
  event: AgentEvent
): event is AgentEvent & { payload: ApprovalRequiredEventPayload } {
  return event.type === AgentEventType.APPROVAL_REQUIRED;
}
