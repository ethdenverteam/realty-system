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
  autopublish_objects_count?: number;
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
  can_publish?: boolean;
  last_publication?: string;
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

// Realty Object types
export interface RealtyObject {
  object_id: string;
  status: string;
  rooms_type?: string | null;
  price: number;
  area?: number | null;
  floor?: string | null;
  districts_json?: string[] | null;
  comment?: string | null;
  address?: string | null;
  renovation?: string | null;
  contact_name?: string | null;
  phone_number?: string | null;
  show_username?: boolean;
  photos_json?: string[] | null;
  creation_date?: string;
  publication_date?: string;
  user_id?: number | string;
  can_publish?: boolean;
  last_publication?: string;
}

export interface ObjectFormData {
  rooms_type: string;
  price: string;
  area: string;
  floor: string;
  districts: string;
  comment: string;
  address: string;
  residential_complex: string;
  renovation: string;
  contact_name: string;
  phone_number: string;
  show_username: boolean;
}

export interface CreateObjectRequest {
  rooms_type: string;
  price: number;
  area?: number | null;
  floor?: string | null;
  districts_json: string[];
  comment?: string | null;
  address?: string | null;
  residential_complex?: string | null;
  renovation?: string | null;
  contact_name?: string | null;
  phone_number?: string | null;
  show_username: boolean;
}

export interface UpdateObjectRequest {
  rooms_type?: string | null;
  price: number;
  area?: number | null;
  floor?: string | null;
  districts_json: string[];
  comment?: string | null;
  address?: string | null;
  residential_complex?: string | null;
  renovation?: string | null;
  contact_name?: string | null;
  phone_number?: string | null;
  show_username: boolean;
}

export interface CreateObjectResponse {
  success?: boolean;
  object_id?: number | string;
  error?: string;
}

export interface ApiErrorResponse {
  error: string;
  message?: string;
}

// Импортируем типы из констант (единый источник истины)
export type { RoomsType, RenovationType, ObjectStatus } from '../utils/constants'

// API Response types
export interface ObjectsListResponse {
  objects: RealtyObjectListItem[];
  total?: number;
  page?: number;
  per_page?: number;
}

// Autopublish types
export interface AutopublishAccountConfig {
  account_id: number;
  chat_ids: (number | string)[];
}

export interface AutopublishAccountsConfig {
  accounts: AutopublishAccountConfig[];
  publication_format?: 'default' | 'compact'; // 'default' - как сейчас, 'compact' - новый формат
}

export interface AutopublishConfigDto {
  config_id: number;
  user_id: number;
  object_id: string;
  enabled: boolean;
  bot_enabled: boolean;
  accounts_config_json?: AutopublishAccountsConfig | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AutopublishItem {
  object: RealtyObjectListItem | RealtyObject;
  config: AutopublishConfigDto;
}

export interface AutopublishListResponse {
  autopublish_items: AutopublishItem[];
  available_objects: RealtyObjectListItem[];
}

export interface PublishObjectRequest {
  object_id: string;
}

export interface PublishObjectResponse {
  success: boolean;
  error?: string;
  message?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: User;
  success?: boolean;
  error?: string;
}

export interface LogsResponse {
  logs?: ActionLogItem[];
  total?: number;
  page?: number;
  per_page?: number;
}

