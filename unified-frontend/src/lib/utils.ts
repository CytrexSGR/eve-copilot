import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format ISK value with proper suffixes
 */
export function formatISK(value: number): string {
  if (value >= 1e12) {
    return `${(value / 1e12).toFixed(2)}T ISK`
  }
  if (value >= 1e9) {
    return `${(value / 1e9).toFixed(2)}B ISK`
  }
  if (value >= 1e6) {
    return `${(value / 1e6).toFixed(2)}M ISK`
  }
  if (value >= 1e3) {
    return `${(value / 1e3).toFixed(2)}K ISK`
  }
  return `${value.toFixed(2)} ISK`
}

/**
 * Format skill points with proper suffixes
 */
export function formatSP(value: number): string {
  if (value >= 1e6) {
    return `${(value / 1e6).toFixed(2)}M SP`
  }
  if (value >= 1e3) {
    return `${(value / 1e3).toFixed(1)}K SP`
  }
  return `${value} SP`
}

/**
 * Format time duration from seconds
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`
  }
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`
  }
  if (seconds < 86400) {
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
  }
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  return hours > 0 ? `${days}d ${hours}h` : `${days}d`
}

/**
 * Format relative time (e.g., "in 2 hours", "3 days ago")
 */
export function formatRelativeTime(date: Date | string): string {
  const now = new Date()
  const target = typeof date === 'string' ? new Date(date) : date
  const diffMs = target.getTime() - now.getTime()
  const diffSeconds = Math.abs(Math.floor(diffMs / 1000))
  const isFuture = diffMs > 0

  const formatted = formatDuration(diffSeconds)
  return isFuture ? `in ${formatted}` : `${formatted} ago`
}
