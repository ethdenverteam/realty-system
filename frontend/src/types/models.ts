export type WebRole = 'admin' | 'user' | (string & {});

export interface User {
  web_role: WebRole;
  [key: string]: unknown;
}

export interface AdminStats {
  users_count: number;
  objects_count: number;
  publications_today: number;
  accounts_count: number;
}

export interface UserStats {
  objects_count: number;
  total_publications: number;
  today_publications: number;
  accounts_count: number;
}

export interface ActionLogItem {
  log_id: number | string;
  created_at: string;
  action: string;
  user_id?: number | string | null;
}

export interface RealtyObjectListItem {
  object_id: number | string;
  status: string;
  rooms_type?: string | null;
  price: number;
  area?: number | null;
  floor?: string | null;
  districts_json?: string[] | null;
  comment?: string | null;
}

export interface BotChatFilters {
  rooms_types?: string[];
  districts?: string[];
  price_min?: number | null;
  price_max?: number | null;
}

export interface BotChatListItem {
  chat_id: number | string;
  title: string;
  telegram_chat_id?: number | string;
  type: string;
  is_active: boolean;
  filters_json?: BotChatFilters | null;
  category?: string | null;
}

export interface BotChatsConfig {
  rooms_types: string[];
  districts?: Record<string, unknown>;
}

export interface FetchedChat {
  id: number | string;
  title: string;
  type: string;
}

export interface FetchedChatsResponse {
  all?: FetchedChat[];
  groups?: FetchedChat[];
  users?: FetchedChat[];
  warning?: string;
}


