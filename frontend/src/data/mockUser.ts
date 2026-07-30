import type { UserSettings } from '../types/course';

export const mockUser: UserSettings = {
  name: 'Nigel Story',
  feedbackTone: 'encouraging',
  thumbnailGenerationEnabled: true,
  modelProvider: {
    tier: 'hosted',
    hostedProvider: 'anthropic',
    apiKey: '',
  },
};
