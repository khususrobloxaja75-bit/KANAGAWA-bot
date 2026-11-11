import discord
from discord.ext import commands
import asyncio
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

TOKEN = os.getenv("TOKEN")
TRIGGER_CHANNEL_ID = int(os.getenv("TRIGGER_CHANNEL_ID", "1570094799573491762"))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"KANAGAWA Bot is Online!")
    def log_message(self, format, *args):
        return

def run_web():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
auto_rooms = {}

class NameModal(discord.ui.Modal, title="Ganti Nama Voice"):
    nama = discord.ui.TextInput(label="Nama baru", placeholder="Contoh: Nongkrong KANAGAWA", max_length=50)
    async def on_submit(self, interaction: discord.Interaction):
        vc = interaction.user.voice.channel if interaction.user.voice else None
        if vc and vc.id in auto_rooms:
            await vc.edit(name=self.nama.value)
            await interaction.response.send_message(f"✅ Nama jadi **{self.nama.value}**", ephemeral=True)
        else:
            await interaction.response.send_message("Kamu bukan owner!", ephemeral=True)

class LimitModal(discord.ui.Modal, title="Atur Limit"):
    limit = discord.ui.TextInput(label="Limit (0 = tanpa limit)", placeholder="Contoh: 5", max_length=2)
    async def on_submit(self, interaction: discord.Interaction):
        vc = interaction.user.voice.channel if interaction.user.voice else None
        if vc and vc.id in auto_rooms:
            try:
                await vc.edit(user_limit=int(self.limit.value))
                await interaction.response.send_message(f"✅ Limit jadi **{self.limit.value}**", ephemeral=True)
            except:
                await interaction.response.send_message("Masukin angka!", ephemeral=True)

class MemberModal(discord.ui.Modal, title="Pilih Member"):
    def __init__(self, action: str):
        super().__init__()
        self.action = action
        self.member_input = discord.ui.TextInput(label="Nama / ID Member", placeholder="Contoh: dimas", max_length=50)
        self.add_item(self.member_input)
    async def on_submit(self, interaction: discord.Interaction):
        vc = interaction.user.voice.channel if interaction.user.voice else None
        if not vc or vc.id not in auto_rooms:
            await interaction.response.send_message("Kamu bukan owner!", ephemeral=True)
            return
        name = self.member_input.value.replace("@","").strip()
        target = discord.utils.find(lambda m: name.lower() in m.display_name.lower() or name == str(m.id), interaction.guild.members)
        if not target:
            await interaction.response.send_message(f"Member **{name}** gak ketemu!", ephemeral=True)
            return
        if self.action == "trust":
            await vc.set_permissions(target, connect=True, speak=True)
            await interaction.response.send_message(f"✅ {target.mention} di-TRUST", ephemeral=True)
        elif self.action == "untrust":
            await vc.set_permissions(target, overwrite=None)
            await interaction.response.send_message(f"❌ {target.mention} di-UNTRUST", ephemeral=True)
        elif self.action == "kick":
            if target.voice and target.voice.channel == vc:
                await target.move_to(None)
                await interaction.response.send_message(f"👢 {target.mention} di-KICK!", ephemeral=True)
            else:
                await interaction.response.send_message("Dia gak di voice ini!", ephemeral=True)
        elif self.action == "block":
            await vc.set_permissions(target, connect=False)
            if target.voice and target.voice.channel == vc:
                await target.move_to(None)
            await interaction.response.send_message(f"🚫 {target.mention} di-BLOCK!", ephemeral=True)
        elif self.action == "unblock":
            await vc.set_permissions(target, overwrite=None)
            await interaction.response.send_message(f"✅ {target.mention} di-UNBLOCK!", ephemeral=True)
        elif self.action == "transfer":
            auto_rooms[vc.id] = target.id
            await vc.set_permissions(interaction.user, overwrite=None)
            await vc.set_permissions(target, manage_channels=True)
            await vc.edit(name=f"└. {target.display_name}")
            await interaction.response.send_message(f"👑 Owner pindah ke {target.mention}!", ephemeral=True)
        elif self.action == "invite":
            await interaction.response.send_message(f"📩 {target.mention}, kamu di-invite ke {vc.mention}!", ephemeral=False)

class TempVoiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="NAME", emoji="✏️", style=discord.ButtonStyle.secondary, custom_id="v_name", row=0)
    async def name_btn(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(NameModal())
    @discord.ui.button(label="LIMIT", emoji="👥", style=discord.ButtonStyle.secondary, custom_id="v_limit", row=0)
    async def limit_btn(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(LimitModal())
    @discord.ui.button(label="PRIVACY", emoji="🔒", style=discord.ButtonStyle.secondary, custom_id="v_privacy", row=0)
    async def privacy_btn(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.user.voice.channel if i.user.voice else None
        if vc and vc.id in auto_rooms:
            perms = vc.overwrites.get(i.guild.default_role)
            is_locked = perms and perms.connect == False
            if is_locked:
                await vc.set_permissions(i.guild.default_role, connect=True)
                await i.response.send_message("🔓 Privacy: **PUBLIC**", ephemeral=True)
            else:
                await vc.set_permissions(i.guild.default_role, connect=False)
                await i.response.send_message("🔒 Privacy: **PRIVATE**", ephemeral=True)
        else:
            await i.response.send_message("Kamu bukan owner!", ephemeral=True)
    @discord.ui.button(label="WAITING ROOM", emoji="⏱️", style=discord.ButtonStyle.secondary, custom_id="v_waiting", row=0)
    async def waiting_btn(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.user.voice.channel if i.user.voice else None
        if vc and vc.id in auto_rooms:
            wr = await i.guild.create_voice_channel(name=f"⏳ Waiting - {vc.name}", category=vc.category)
            await i.response.send_message(f"⏱️ Waiting Room: {wr.mention}", ephemeral=True)
        else:
            await i.response.send_message("Kamu bukan owner!", ephemeral=True)
    @discord.ui.button(label="CHAT", emoji="💬", style=discord.ButtonStyle.secondary, custom_id="v_chat", row=0)
    async def chat_btn(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.user.voice.channel if i.user.voice else None
        if vc and vc.id in auto_rooms:
            ch = await i.guild.create_text_channel(name=f"💬-{vc.name.lower().replace(' ','-')[:20]}", category=vc.category)
            await ch.set_permissions(i.guild.default_role, view_channel=False)
            await ch.set_permissions(i.user, view_channel=True)
            await i.response.send_message(f"💬 Chat: {ch.mention}", ephemeral=True)
        else:
            await i.response.send_message("Kamu bukan owner!", ephemeral=True)
    @discord.ui.button(label="TRUST", emoji="👤", style=discord.ButtonStyle.secondary, custom_id="v_trust", row=1)
    async def trust_btn(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(MemberModal("trust"))
    @discord.ui.button(label="UNTRUST", emoji="🚫", style=discord.ButtonStyle.secondary, custom_id="v_untrust", row=1)
    async def untrust_btn(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(MemberModal("untrust"))
    @discord.ui.button(label="INVITE", emoji="📞", style=discord.ButtonStyle.secondary, custom_id="v_invite", row=1)
    async def invite_btn(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(MemberModal("invite"))
    @discord.ui.button(label="KICK", emoji="📵", style=discord.ButtonStyle.secondary, custom_id="v_kick", row=1)
    async def kick_btn(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(MemberModal("kick"))
    @discord.ui.button(label="REGION", emoji="🌍", style=discord.ButtonStyle.secondary, custom_id="v_region", row=1)
    async def region_btn(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.user.voice.channel if i.user.voice else None
        if vc and vc.id in auto_rooms:
            await vc.edit(rtc_region="singapore")
            await i.response.send_message("🌍 Region: **Singapore**", ephemeral=True)
        else:
            await i.response.send_message("Kamu bukan owner!", ephemeral=True)
    @discord.ui.button(label="BLOCK", emoji="🚫", style=discord.ButtonStyle.secondary, custom_id="v_block", row=2)
    async def block_btn(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(MemberModal("block"))
    @discord.ui.button(label="UNBLOCK", emoji="✅", style=discord.ButtonStyle.secondary, custom_id="v_unblock", row=2)
    async def unblock_btn(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(MemberModal("unblock"))
    @discord.ui.button(label="CLAIM", emoji="👑", style=discord.ButtonStyle.secondary, custom_id="v_claim", row=2)
    async def claim_btn(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.user.voice.channel if i.user.voice else None
        if vc and vc.id in auto_rooms:
            owner = i.guild.get_member(auto_rooms[vc.id])
            if owner and owner in vc.members:
                await i.response.send_message(f"Owner masih ada: {owner.mention}!", ephemeral=True)
            else:
                auto_rooms[vc.id] = i.user.id
                await vc.edit(name=f"└. {i.user.display_name}")
                await i.response.send_message(f"👑 Kamu jadi owner {vc.mention}!", ephemeral=True)
        else:
            await i.response.send_message("Bukan temp voice!", ephemeral=True)
    @discord.ui.button(label="TRANSFER", emoji="👑", style=discord.ButtonStyle.secondary, custom_id="v_transfer", row=2)
    async def transfer_btn(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(MemberModal("transfer"))
    @discord.ui.button(label="DELETE", emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="v_delete", row=2)
    async def delete_btn(self, i: discord.Interaction, b: discord.ui.Button):
        vc = i.user.voice.channel if i.user.voice else None
        if vc and vc.id in auto_rooms and auto_rooms[vc.id] == i.user.id:
            del auto_rooms[vc.id]
            await vc.delete(reason="Dihapus owner")
            await i.response.send_message("🗑️ Room dihapus!", ephemeral=True)
        else:
            await i.response.send_message("Cuma owner yang bisa hapus!", ephemeral=True)

async def kirim_panel_ke_voice(voice_channel, owner):
    embed = discord.Embed(
        description=f"**Halo {owner.mention}! Ini room kamu.**\nThis interface can be used to manage temporary voice channels.\nMore options are available with **/voice** commands.\n\nPress the buttons below to use the interface",
        color=0xff2d55
    )
    embed.set_footer(text="KANAGAWA • Temp Voice Control")
    try:
        await voice_channel.send(embed=embed, view=TempVoiceView())
    except Exception as e:
        print(f"Gagal kirim panel: {e}")

@bot.event
async def on_ready():
    print(f"Bot {bot.user} udah online!")
    try:
        synced = await bot.tree.sync()
        print(f"Sync {len(synced)} command!")
    except Exception as e:
        print(e)

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == TRIGGER_CHANNEL_ID:
        new_ch = await member.guild.create_voice_channel(name=f"└. {member.display_name}", category=after.channel.category)
        auto_rooms[new_ch.id] = member.id
        await member.move_to(new_ch)
        await new_ch.set_permissions(member, manage_channels=True, move_members=True)
        await asyncio.sleep(1)
        await kirim_panel_ke_voice(new_ch, member)
    if before.channel and before.channel.id in auto_rooms:
        if len(before.channel.members) == 0:
            try:
                del auto_rooms[before.channel.id]
                await before.channel.delete()
            except: pass

@bot.tree.command(name="voice", description="Kirim panel Temp Voice KANAGAWA")
async def voice_panel(interaction: discord.Interaction):
    embed = discord.Embed(description="**This interface can be used to manage temporary voice channels.**\nMore options are available with **/voice** commands.\n\nPress the buttons below to use the interface", color=0xff2d55)
    await interaction.response.send_message("Panel dikirim!")
    await interaction.channel.send(embed=embed, view=TempVoiceView())

bot.run(TOKEN)
