import { format } from 'date-fns';

export const formatDateToYMD = (date: Date): string => format(date, 'yyyy-MM-dd');

export const getTodayDateString = (): string => formatDateToYMD(new Date());

export const isSameDateString = (a: string, b: string): boolean => a === b;

