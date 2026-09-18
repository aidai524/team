/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export enum AI_EDITOR_TASKS {
  ASK_ANYTHING = "ASK_ANYTHING",
  PARAPHRASE = "PARAPHRASE",
  SIMPLIFY = "SIMPLIFY",
  ELABORATE = "ELABORATE",
  SUMMARIZE = "SUMMARIZE",
  TITLE = "TITLE",
}

export const LOADING_TEXTS = {
  [AI_EDITOR_TASKS.ASK_ANYTHING]: "AI is generating response",
  [AI_EDITOR_TASKS.PARAPHRASE]: "AI is paraphrasing",
  [AI_EDITOR_TASKS.SIMPLIFY]: "AI is simplifying",
  [AI_EDITOR_TASKS.ELABORATE]: "AI is elaborating",
  [AI_EDITOR_TASKS.SUMMARIZE]: "AI is summarizing",
  [AI_EDITOR_TASKS.TITLE]: "AI is generating a title",
} satisfies { [key in AI_EDITOR_TASKS]: string };
