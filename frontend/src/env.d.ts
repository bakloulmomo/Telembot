/// <reference types="vite/client" />

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<object, object, unknown>;
  export default component;
}

declare module "@voice" {
  export type VoiceState = "idle" | "listening" | "transcribing";
  export interface VoiceInput {
    mode: "server" | "browser" | null;
    readonly state: VoiceState;
    toggle(): void;
    cancel(): void;
  }
  export function createVoiceInput(options: {
    apiBase?: string;
    lang?: string | null;
    onText: (text: string) => void;
    onState?: (state: VoiceState) => void;
    onError?: (message: string) => void;
  }): Promise<VoiceInput>;
}
