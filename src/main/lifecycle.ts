let quitting = false;

export const isQuitting = (): boolean => quitting;

export const markQuitting = (): void => {
  quitting = true;
};

