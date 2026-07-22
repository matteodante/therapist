import { defineTool, dispatch } from '@flue/runtime';
import {
  createTelegramChannel,
  type TelegramConversationRef,
  type Update,
} from '@flue/telegram';
import { Api } from 'grammy';
import * as v from 'valibot';
import therapist from '../agents/therapist.ts';
import { clearPersonalMemoryIndex, retainUserMessage } from '../services/hindsight.ts';
import { transcribeTelegramVoice } from '../services/stt.ts';
import { requiredEnv } from '../shared/env.ts';
import { logError, logEvent } from '../shared/log.ts';
import { isAllowedPrivateMessage, splitTelegramText } from '../shared/telegram.ts';
import { claimTelegramUpdate, clearStructuredMemory } from '../storage/app-db.ts';

type TelegramMessage = NonNullable<Update['message']>;

const botToken = requiredEnv('TELEGRAM_BOT_TOKEN');
const webhookSecret = requiredEnv('TELEGRAM_WEBHOOK_SECRET_TOKEN');
const allowedUserId = Number(requiredEnv('TELEGRAM_ALLOWED_USER_ID'));

if (!Number.isSafeInteger(allowedUserId)) {
  throw new Error('TELEGRAM_ALLOWED_USER_ID must be a numeric Telegram user ID.');
}

export const client = new Api(botToken);

export const channel = createTelegramChannel({
  secretToken: webhookSecret,

  async webhook({ update }) {
    const incoming = update.message;
    if (!incoming) return;

    if (!isAllowedPrivateMessage(incoming, allowedUserId)) {
      logEvent('telegram.message_rejected', {
        updateId: update.update_id,
        chatType: incoming.chat.type,
        fromId: incoming.from?.id,
      });
      return;
    }

    if (!claimTelegramUpdate(update.update_id)) {
      logEvent('telegram.duplicate_update_ignored', { updateId: update.update_id });
      return;
    }

    const commandHandled = await handleStaticCommand(incoming, String(incoming.from!.id));
    if (commandHandled) return;

    try {
      await client.sendChatAction(incoming.chat.id, 'typing');
      const body = await messageBody(incoming);
      if (!body) {
        await client.sendMessage(
          incoming.chat.id,
          'Per ora posso ricevere testo e messaggi vocali.',
        );
        return;
      }

      const userKey = String(incoming.from!.id);
      await retainUserMessage(userKey, body, {
        updateId: String(update.update_id),
        telegramMessageId: String(incoming.message_id),
        inputModality: incoming.voice ? 'voice' : 'text',
        languageCode: incoming.from?.language_code ?? '',
      });

      const conversation = conversationFromMessage(incoming);
      await dispatch(therapist, {
        id: channel.conversationKey(conversation),
        input: {
          type: 'telegram.message',
          body,
          attributes: {
            updateId: String(update.update_id),
            fromId: userKey,
            inputModality: incoming.voice ? 'voice' : 'text',
            ...(incoming.from?.username ? { fromUsername: incoming.from.username } : {}),
            ...(incoming.from?.language_code
              ? { languageCode: incoming.from.language_code }
              : {}),
          },
        },
      });
    } catch (error) {
      logError('telegram.message_processing_failed', error, {
        updateId: update.update_id,
      });
      await client.sendMessage(
        incoming.chat.id,
        'Non sono riuscito a elaborare questo messaggio. Riprova tra poco.',
      );
    }
  },
});

async function handleStaticCommand(
  message: TelegramMessage,
  userKey: string,
): Promise<boolean> {
  const text = message.text?.trim();
  if (!text?.startsWith('/')) return false;

  const [commandToken = '', ...commandArguments] = text.split(/\s+/);
  const command = commandToken.split('@', 1)[0]?.toLowerCase();

  if (command === '/start') {
    await client.sendMessage(
      message.chat.id,
      [
        'Sono Therapist, un agente personale per supporto psicologico e auto-riflessione.',
        '',
        'Ricordo il percorso nel tempo e seguo protocolli strutturati, ma non sono uno psicologo abilitato né un servizio di emergenza.',
        '',
        'Puoi scrivere o inviare un vocale.',
      ].join('\n'),
    );
    return true;
  }

  if (command === '/help') {
    await client.sendMessage(
      message.chat.id,
      [
        'Scrivi liberamente ciò che vuoi esplorare.',
        '',
        '/privacy — informazioni essenziali sui dati',
        '/status — verifica che il bot sia online',
        '/clear-derived-memory confirm — cancella memoria strutturata e indice semantico',
      ].join('\n'),
    );
    return true;
  }

  if (command === '/privacy') {
    await client.sendMessage(
      message.chat.id,
      [
        'Il modello, la cronologia e la memoria possono essere eseguiti localmente.',
        'I messaggi transitano comunque attraverso Telegram e le chat con i bot non sono Secret Chats end-to-end encrypted.',
        'I vocali vengono scaricati, trascritti e non salvati dall’applicazione.',
      ].join('\n'),
    );
    return true;
  }

  if (command === '/status') {
    await client.sendMessage(message.chat.id, 'Therapist è online.');
    return true;
  }

  if (command === '/clear-derived-memory') {
    if (commandArguments.join(' ') !== 'confirm') {
      await client.sendMessage(
        message.chat.id,
        'Per confermare usa esattamente: /clear-derived-memory confirm',
      );
      return true;
    }

    const deleted = clearStructuredMemory(userKey);
    const { failedDocuments } = await clearPersonalMemoryIndex(userKey);
    const semanticStatus = failedDocuments === 0
      ? 'Anche l’indice semantico è stato cancellato.'
      : `Non è stato possibile cancellare completamente l’indice semantico (${failedDocuments} operazioni fallite).`;
    await client.sendMessage(
      message.chat.id,
      `Memoria strutturata cancellata (${deleted} record). ${semanticStatus} La cronologia canonica di Flue non viene eliminata da questo comando.`,
    );
    return true;
  }

  return false;
}

async function messageBody(message: TelegramMessage): Promise<string | null> {
  if (message.text !== undefined) return message.text.trim();
  if (message.caption !== undefined) return message.caption.trim();
  if (message.voice) {
    return transcribeTelegramVoice(
      client,
      botToken,
      message.voice.file_id,
      message.voice.file_size,
    );
  }
  return null;
}

function conversationFromMessage(message: TelegramMessage): TelegramConversationRef {
  return {
    type: 'chat',
    chatId: message.chat.id,
  };
}

export function postTelegramMessage(ref: TelegramConversationRef, userKey: string) {
  return defineTool({
    name: 'post_telegram_message',
    description:
      'Post the final user-facing reply to the Telegram conversation bound by trusted application code. Call exactly once after completing memory and skill work.',
    input: v.object({
      text: v.pipe(v.string(), v.minLength(1), v.maxLength(24_000)),
    }),
    output: v.object({
      delivered: v.boolean(),
      messageIds: v.array(v.number()),
    }),
    async run({ input }) {
      const messageIds: number[] = [];
      for (const chunk of splitTelegramText(input.text)) {
        const message = await client.sendMessage(ref.chatId, chunk);
        messageIds.push(message.message_id);
      }

      logEvent('telegram.reply_delivered', {
        chatId: String(ref.chatId),
        chunks: messageIds.length,
      });

      return {
        delivered: true,
        messageIds,
      };
    },
  });
}
