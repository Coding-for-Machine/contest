export interface AuthUser {
  id?: number | string;
  telegramId?: number | string;
  username: string;
  phone?: string | null;
  fullName?: string | null;
  lastLogin?: string | null;
  avatar?: string | null;
  role?: string;
}

export interface ContestPrize {
  id: number;
  rank_target: number;
  title: string;
  description?: string;
}
