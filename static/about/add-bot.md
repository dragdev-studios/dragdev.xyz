# Bot Addition Guidelines
Yes, we accept bot submissions. You can have your own bot here if you want, and if it meets the below standards. Our bots also follow a lot of these guidelines during development, so that's fun!
__Note that we will not add bots that are low quality or have poor uptime.__ Also, generic bots or clones like discord red are not allowed.

## Your bot MUST:
1. have a non-common prefix, or allow customisable ones.
2. clean all echoed user input. this means if someone says "@yourbot say @everyone sucks", your bot must respond with a cleaned version of the mention. Even though your bot will not have permissions to mention everyone, pretend it did. (want a tip? A common way to clean mentions is to add a zero width space (u200b) after the `@` character).
3. only respond to commands. Basically, your bot shouldn't randomly say "hey, what's up!". Also, __level messages are forbidden__. However, timers and reminders are okay, since they were user-invoked.
4. be original. As stated above, we won't accept clones or forks of other bots.

## Your bot MUST NOT:
1. respond with "command not found" when someone runs a command that doesn't exist. This is just annoying and helps nobody.
2. respond to other bots. If it does, you shouldn't be making a bot. This is discord bot creation 101.
3. have exposed admin/dev commands. We will test common developer-only and admin-only commands before we add your bot. If we're able to run any, your bot will be denied.
4. have advertisements. Links to your server in commands like [p]info are perfectly fine.
5. be intrusive or obnoxious.

## Ready to submit?
Great! Head over to the server and run `t!new add bot` in 
[#bot-commands](https://discord.com/channels/772980293929402389/772984113158160395), go to your ticket, and send your 
bot's invite link!

Make sure you pay attention to the ticket as admins will inform you of your bot's status there, and may ask you 
questions if needed.
