"use client";

import { BarChart3, Coins, HandCoins, House, MoreHorizontal, Settings2, SlidersHorizontal } from "lucide-react";

export const navItems = [
  { href: "/", label: "대시보드", icon: House },
  { href: "/holdings", label: "보유 종목", icon: Coins },
  { href: "/dividends", label: "실수령 배당", icon: HandCoins },
  { href: "/projection", label: "배당 추정", icon: BarChart3 },
  { href: "/rules", label: "투자 규칙", icon: SlidersHorizontal },
  { href: "/settings", label: "설정", icon: Settings2 },
] as const;

export const mobilePrimaryNavItems = navItems.slice(0, 4);
export const mobileOverflowNavItems = navItems.slice(4);
export const mobileMoreIcon = MoreHorizontal;
