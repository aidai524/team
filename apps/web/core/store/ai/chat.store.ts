/**
 * MobX store for the AI chat panel.
 */

import { action, makeObservable, observable, runInAction } from "mobx";
// services
import {
  createSkill,
  deleteSkill,
  executeActions,
  fetchSessions,
  fetchSessionMessages,
  fetchSkills,
  fetchUsage,
  streamChat,
} from "@/services/ai/ai-gateway.service";
import type {
  TAIChatMessage,
  TAIChatMode,
  TAIExecutionResult,
  TAIProposedAction,
  TAISession,
  TAISkill,
  TAIUsage,
} from "@/services/ai/ai-gateway.service";

let messageSeq = 0;
const nextMessageId = () => `ai-msg-${++messageSeq}`;

export interface IAIChatStore {
  // observables
  isOpen: boolean;
  isFullScreen: boolean;
  isStreaming: boolean;
  isExecuting: boolean;
  error: string | null;
  messages: TAIChatMessage[];
  conversationId: string | null;
  sessions: TAISession[];
  mode: TAIChatMode;
  proposedActions: TAIProposedAction[];
  executionResults: TAIExecutionResult[];
  skills: TAISkill[];
  usage: TAIUsage | null;
  // actions
  toggle: () => void;
  open: () => void;
  close: () => void;
  toggleFullScreen: () => void;
  newConversation: () => void;
  setMode: (mode: TAIChatMode) => void;
  sendMessage: (text: string, workspaceSlug: string) => Promise<void>;
  confirmPlan: (workspaceSlug: string) => Promise<void>;
  cancelPlan: () => void;
  removeAction: (index: number) => void;
  loadSessions: (workspaceSlug: string) => Promise<void>;
  loadSkills: (workspaceSlug: string) => Promise<void>;
  loadUsage: (workspaceSlug: string) => Promise<void>;
  addSkill: (workspaceSlug: string, name: string, prompt: string) => Promise<void>;
  removeSkill: (skillId: string, workspaceSlug: string) => Promise<void>;
  loadConversation: (conversationId: string) => Promise<void>;
}

export class AIChatStore implements IAIChatStore {
  isOpen = false;
  isFullScreen = false;
  isStreaming = false;
  isExecuting = false;
  error: string | null = null;
  messages: TAIChatMessage[] = [];
  conversationId: string | null = null;
  sessions: TAISession[] = [];
  mode: TAIChatMode = "ask";
  proposedActions: TAIProposedAction[] = [];
  executionResults: TAIExecutionResult[] = [];
  skills: TAISkill[] = [];
  usage: TAIUsage | null = null;

  private abortController: AbortController | null = null;

  constructor() {
    makeObservable(this, {
      isOpen: observable,
      isFullScreen: observable,
      isStreaming: observable,
      isExecuting: observable,
      error: observable,
      messages: observable,
      conversationId: observable,
      sessions: observable,
      mode: observable,
      proposedActions: observable,
      executionResults: observable,
      skills: observable,
      usage: observable,
      toggle: action,
      open: action,
      close: action,
      toggleFullScreen: action,
      newConversation: action,
      setMode: action,
      sendMessage: action,
      confirmPlan: action,
      cancelPlan: action,
      removeAction: action,
      loadSessions: action,
      loadSkills: action,
      loadUsage: action,
      addSkill: action,
      removeSkill: action,
      loadConversation: action,
    });
  }

  toggle = () => {
    this.isOpen = !this.isOpen;
  };

  open = () => {
    this.isOpen = true;
  };

  close = () => {
    this.isOpen = false;
  };

  toggleFullScreen = () => {
    this.isFullScreen = !this.isFullScreen;
  };

  setMode = (mode: TAIChatMode) => {
    this.mode = mode;
  };

  newConversation = () => {
    this.abortController?.abort();
    this.messages = [];
    this.conversationId = null;
    this.error = null;
    this.isStreaming = false;
    this.proposedActions = [];
    this.executionResults = [];
  };

  sendMessage = async (text: string, workspaceSlug: string) => {
    const trimmed = text.trim();
    if (!trimmed || this.isStreaming) return;

    this.error = null;
    this.proposedActions = [];
    this.executionResults = [];
    this.messages.push({ id: nextMessageId(), role: "user", content: trimmed });

    const assistant: TAIChatMessage = {
      id: nextMessageId(),
      role: "assistant",
      content: "",
      isStreaming: true,
      toolActivity: [],
    };
    this.messages.push(assistant);
    this.isStreaming = true;
    this.abortController = new AbortController();

    try {
      await streamChat(
        { message: trimmed, workspaceSlug, conversationId: this.conversationId, mode: this.mode },
        (event) => {
          runInAction(() => {
            switch (event.type) {
              case "token":
                assistant.content += event.content ?? "";
                break;
              case "tool_call":
                if (event.name) assistant.toolActivity = [...(assistant.toolActivity ?? []), event.name];
                break;
              case "plan":
                this.proposedActions = event.actions ?? [];
                if ((event.actions ?? []).length > 0) {
                  assistant.content = "已生成执行计划，请确认：";
                }
                break;
              case "sources":
                assistant.sources = [...(assistant.sources ?? []), ...(event.sources ?? [])];
                break;
              case "done":
                if (event.conversationId) this.conversationId = event.conversationId;
                break;
              case "error":
                this.error = event.message ?? "AI 返回错误";
                break;
              default:
                break;
            }
          });
        },
        this.abortController.signal
      );
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : String(err);
      });
    } finally {
      runInAction(() => {
        assistant.isStreaming = false;
        this.isStreaming = false;
        this.abortController = null;
      });
    }
  };

  confirmPlan = async (workspaceSlug: string) => {
    if (this.proposedActions.length === 0 || this.isExecuting) return;
    this.isExecuting = true;
    this.error = null;
    try {
      const results = await executeActions({
        workspaceSlug,
        conversationId: this.conversationId,
        actions: this.proposedActions,
      });
      runInAction(() => {
        this.executionResults = results;
        this.proposedActions = [];
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : String(err);
      });
    } finally {
      runInAction(() => {
        this.isExecuting = false;
      });
    }
  };

  cancelPlan = () => {
    this.proposedActions = [];
  };

  removeAction = (index: number) => {
    this.proposedActions = this.proposedActions.filter((_, i) => i !== index);
  };

  loadSessions = async (workspaceSlug: string) => {
    try {
      const sessions = await fetchSessions(workspaceSlug);
      runInAction(() => {
        this.sessions = sessions;
      });
    } catch {
      // Session history is non-critical; leave the existing list intact.
    }
  };

  loadSkills = async (workspaceSlug: string) => {
    try {
      const skills = await fetchSkills(workspaceSlug);
      runInAction(() => {
        this.skills = skills;
      });
    } catch {
      // Skills list is non-critical.
    }
  };

  loadUsage = async (workspaceSlug: string) => {
    try {
      const usage = await fetchUsage(workspaceSlug);
      runInAction(() => {
        this.usage = usage;
      });
    } catch {
      // Usage is non-critical.
    }
  };

  addSkill = async (workspaceSlug: string, name: string, prompt: string) => {
    await createSkill({ workspaceSlug, name, prompt });
    await this.loadSkills(workspaceSlug);
  };

  removeSkill = async (skillId: string, workspaceSlug: string) => {
    await deleteSkill(skillId, workspaceSlug);
    runInAction(() => {
      this.skills = this.skills.filter((s) => s.id !== skillId);
    });
  };

  loadConversation = async (conversationId: string) => {
    try {
      const history = await fetchSessionMessages(conversationId);
      runInAction(() => {
        this.conversationId = conversationId;
        this.messages = history.map((m) => ({
          id: nextMessageId(),
          role: m.role,
          content: m.content,
        }));
        this.error = null;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : String(err);
      });
    }
  };
}
