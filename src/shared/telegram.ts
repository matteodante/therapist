import type { Message } from 'grammy/types';

export function isAllowedPrivateMessage(message: Message, allowedUserId: number): boolean {
  return (
    message.chat.type === 'private' &&
    message.from !== undefined &&
    message.from.id === allowedUserId
  );
}

export function splitTelegramText(text: string, maxLength = 4000): string[] {
  const normalized = text.trim();
  if (!normalized) return [];
  if (normalized.length <= maxLength) return [normalized];

  const chunks: string[] = [];
  let remaining = normalized;

  while (remaining.length > maxLength) {
    const window = remaining.slice(0, maxLength + 1);
    const paragraphBreak = window.lastIndexOf('\n\n');
    const lineBreak = window.lastIndexOf('\n');
    const sentenceBreak = Math.max(
      window.lastIndexOf('. '),
      window.lastIndexOf('? '),
      window.lastIndexOf('! '),
    );
    const space = window.lastIndexOf(' ');

    const splitAt =
      paragraphBreak > maxLength * 0.5
        ? paragraphBreak
        : lineBreak > maxLength * 0.6
          ? lineBreak
          : sentenceBreak > maxLength * 0.6
            ? sentenceBreak + 1
            : space > maxLength * 0.6
              ? space
              : maxLength;

    chunks.push(remaining.slice(0, splitAt).trim());
    remaining = remaining.slice(splitAt).trim();
  }

  if (remaining) chunks.push(remaining);
  return chunks;
}
