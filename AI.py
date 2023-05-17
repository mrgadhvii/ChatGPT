import re
import json
import threading
from md2tgmd import escape
from runasync import run_async
from config import API, NICK, COOKIES
from revChatGPT.V3 import Chatbot as GPT
from telegram.constants import ChatAction
from EdgeGPT import Chatbot as BingAI, ConversationStyle

class AIBot:
    def __init__(self):
        self.bingcookie = COOKIES
        self.conversationStyle = ConversationStyle.balanced

        if self.bingcookie:
            try:
                self.Bingbot = BingAI(cookies=json.loads(self.bingcookie))
            except Exception as e:
                print('\033[31m')
                print("Bing 登陆失败！请更换 COOKIES")
                print("error", e)
                print('\033[0m')
                self.bingcookie = None
        if API:
            self.ChatGPTbot = GPT(api_key=f"{API}")

        self.botNick = NICK.lower() if NICK else None
        self.botNicKLength = len(self.botNick) if self.botNick else 0
        print("nick:", self.botNick)

    async def getBing(self, message, update, context):
        messageid = 0
        result = ''
        prompt = ""
        modifytime = 0
        try:
            # creative balanced precise
            # result = self.Bingbot.ask_stream(prompt=prompt + message, conversation_style=self.conversationStyle)
            async for result in self.Bingbot.ask_stream(prompt=prompt + message, conversation_style=self.conversationStyle):
                if result[0] == True:
                    break
                if "[1]:" in result[1].split("\n\n")[0]:
                    result = "\n\n".join(result[1].split("\n\n")[1:])
                    result = re.sub(r"\[\^\d+\^\]", '', result)
                else:
                    result = result[1]
                    result = re.sub(r"\[\^\d+\^\]", '', result)
                print(str(modifytime) + " " + result, end="\r", flush=True)
                if result.count("```") % 2 != 0:
                    result = result + "\n```"
                result = f"🤖️ Bing\n\n" + result
                if messageid == 0:
                    message = await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=escape(result),
                        parse_mode='MarkdownV2',
                        reply_to_message_id=update.message.message_id,
                    )
                    messageid = message.message_id
                else:
                    modifytime = modifytime + 1
                    try:
                        if modifytime < 128:
                            await context.bot.edit_message_text(chat_id=update.message.chat_id, message_id=messageid, text=escape(result), parse_mode='MarkdownV2')
                        else:
                            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=messageid)
                            messageid = 0
                            modifytime = 0
                    except:
                        pass
            result = result[1]
            numMessages = result["item"]["throttling"]["numUserMessagesInConversation"]
            maxNumMessages = result["item"]["throttling"]["maxNumUserMessagesInConversation"]
            # print(numMessages, "/", maxNumMessages, end="")
            message = result["item"]["messages"][1]["text"]
            print(result["item"]["messages"][1]["text"])
            try:
                print("\n\n" + result["item"]["messages"][1]["adaptiveCards"][0]["body"][0]["text"])
                learnmoretext = result["item"]["messages"][1]["adaptiveCards"][0]["body"][1]["text"]
            except:
                learnmoretext = ""
            result = f"🤖️ Bing {numMessages} / {maxNumMessages} \n\n" + message + "\n\n" + learnmoretext
            await context.bot.edit_message_text(chat_id=update.message.chat_id, message_id=messageid, text=escape(result), parse_mode='MarkdownV2')

            # # creative balanced precise
            # result = await self.Bingbot.ask(prompt=prompt + message, conversation_style=ConversationStyle.creative)
            # # print(result)
            # numMessages = result["item"]["throttling"]["numUserMessagesInConversation"]
            # maxNumMessages = result["item"]["throttling"]["maxNumUserMessagesInConversation"]
            # print(numMessages, "/", maxNumMessages, end="")
            # message = result["item"]["messages"][1]["text"]
            # print(result["item"]["messages"][1]["text"])
            # try:
            #     print("\n\n" + result["item"]["messages"][1]["adaptiveCards"][0]["body"][0]["text"])
            #     learnmoretext = result["item"]["messages"][1]["adaptiveCards"][0]["body"][1]["text"]
            # except:
            #     learnmoretext = ""
            # result = message + "\n\n" + learnmoretext
            # message = await context.bot.send_message(
            #     chat_id=update.message.chat_id,
            #     text=escape(f"🤖️ Bing {numMessages} / {maxNumMessages} \n\n" + result),
            #     parse_mode='MarkdownV2',
            #     reply_to_message_id=update.message.message_id,
            # )

            if numMessages == maxNumMessages:
                await self.Bingbot.reset()
        except Exception as e:
            print('\033[31m')
            print("response_msg", result)
            print("error", e)
            print('\033[0m')
            numMessages = 0
            maxNumMessages = 0
            result = "实在不好意思，我现在无法对此做出回应。 要不我们换个话题？"
            await self.Bingbot.reset()
        result = re.sub(r"\[\^\d+\^\]", '', result)
        print(" BingAI", result)
    
    async def resetBing(self):
        await self.Bingbot.reset()
    
    async def getChatGPT(self, message, update, context):
        result = ''
        try:
            result = self.ChatGPTbot.ask(message)
            message = await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=escape("🤖️ ChatGPT3.5\n\n" + result),
                parse_mode='MarkdownV2',
                reply_to_message_id=update.message.message_id,
            )
        except Exception as e:
            print('\033[31m')
            print("response_msg", result)
            print("error", e)
            print('\033[0m')
            if "overloaded" in str(e):
                result = "OpenAI 服务器过载。"
            else:
                result = "ChatGPT 出错啦。"
            self.ChatGPTbot.reset()
        print("ChatGPT", result)

    async def getResult(self, update, context):
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)
        # self.LastMessage_id = ''
        print("\033[32m", update.effective_user.username, update.effective_user.id, update.message.text, "\033[0m")
        chat_content = update.message.text if NICK is None else update.message.text[self.botNicKLength:].strip() if update.message.text[:self.botNicKLength].lower() == self.botNick else None
        if self.bingcookie and chat_content:
            _thread = threading.Thread(target=run_async, args=(self.getBing(chat_content, update, context),))
            _thread.start()
        if API and chat_content:
            await self.getChatGPT(chat_content, update, context)

    async def reset_chat(self, update, context):
        if API:
            self.ChatGPTbot.reset()
        if self.bingcookie:
            await self.resetBing()
        await context.bot.send_message(
            chat_id=update.message.chat_id,
            text="重置成功！",
        )

    async def creative_bing(self, update, context):
        await self.reset_chat(update, context)
        self.conversationStyle = ConversationStyle.creative

    async def balanced_bing(self, update, context):
        await self.reset_chat(update, context)
        self.conversationStyle = ConversationStyle.balanced

    async def precise_bing(self, update, context):
        await self.reset_chat(update, context)
        self.conversationStyle = ConversationStyle.precise

    async def en2zhtranslator(self, update, context):
        prompt = "I want you to act as a chinese translator. I will speak to you in any language and you will detect the language, translate it and answer in the corrected and improved version of my text, in Chinese. Keep the meaning same, but make them more literary. I want you to only reply the correction, the improvements and nothing else, do not write explanations. My first sentence is \""
        if len(context.args) > 0:
            message = ' '.join(context.args)
            chat_content = prompt + message + '"'
            print("\033[32m")
            print("en2zh", message)
            print("\033[0m")
            if API and message:
                await self.getChatGPT(chat_content, update, context)
                # self.LastMessage_id = ''
                # self.mess = ''
        else:
            message = await context.bot.send_message(
                chat_id=update.message.chat_id,
                text="请在命令后面放入要翻译的文本。",
                parse_mode='MarkdownV2',
                reply_to_message_id=update.message.message_id,
            )