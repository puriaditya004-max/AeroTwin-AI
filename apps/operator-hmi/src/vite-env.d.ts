/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CONTROL_API_URL?: string;
  readonly VITE_HMI_MODE?: string;
  readonly VITE_DEFAULT_MISSION_ID?: string;
  readonly VITE_DEFAULT_ENGINE_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
