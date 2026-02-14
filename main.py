import js
from pyodide.ffi import create_proxy
import random
import asyncio
import json
from datetime import datetime

DEFAULT_WORDS = ["Огън", "Вода", "Въздух", "Земя", "Космос", "Време", "Любов", "Война", "Мир", "Слънце", "Луна", "Звезда", "План", "Ключ", "Врата", "Прозорец", "Книга", "Молив", "Хартия", "Град", "Село", "Планина", "Море", "Река", "Дърво", "Машина", "Кръг", "Център", "Път", "Око", "Ръка", "Сърце", "Глава", "Закон", "История", "Музика", "Театър", "Кино", "Спорт", "Игра", "Карта", "Писмо", "Телефон", "Радио", "Екран", "Компютър", "Мрежа", "Облак", "Дъжд", "Сняг", "Вятър", "Буря", "Пясък", "Камък", "Злато", "Сребро", "Желязо", "Мед", "Стъкло", "Плат", "Хляб", "Вино", "Мляко", "Плод", "Цвете", "Билка", "Птица", "Риба", "Кон", "Куче", "Котка", "Лъв", "Орел", "Змия", "Пчела", "Кораб", "Кола", "Влак", "Мост", "Кула", "Храм", "Дворец", "Къща", "Училище", "Болница", "Пазар", "Улица", "Парк", "Гора", "Поле", "Остров", "Брег", "Връх", "Долина", "Извор", "Пещера", "Огледало", "Часовник", "Свещ", "Лампа"]

class TeamColor:
    GREEN, RED, BLUE, YELLOW, NEUTRAL, BOMB = 'green', 'red', 'blue', 'yellow', 'neutral', 'bomb'

TEAM_THEMES = {
    TeamColor.GREEN: "bg-emerald-600 border-emerald-400 text-white", 
    TeamColor.RED: "bg-red-600 border-red-400 text-white",
    TeamColor.BLUE: "bg-blue-600 border-blue-400 text-white", 
    TeamColor.YELLOW: "bg-amber-500 border-amber-300 text-slate-900",
    TeamColor.NEUTRAL: "bg-slate-100 border-slate-300 text-slate-800", 
    TeamColor.BOMB: "bg-zinc-900 border-zinc-600 text-white",
}

class GameManager:
    def __init__(self):
        js.window.gameManager = self
        self.container = js.document.getElementById("main-content")
        self.player_name = js.localStorage.getItem("codenames_player_name") or ""
        self.current_room_name = ""
        self.player_team, self.player_role = None, None
        self.phase = "LOBBY"
        self.selected_team_count = 2
        self.occupied_roles = {}
        self.reset_state()
        
        close_btn = js.document.getElementById("alert-close")
        if close_btn:
            close_btn.onclick = create_proxy(lambda e: js.document.getElementById("custom-alert").classList.add("hidden"))
            
        self.show_lobby()

    def reset_state(self):
        self.cards, self.teams_state, self.current_team_idx, self.clue, self.chats, self.words_per_team = [], [], 0, None, {}, 8

    def show_alert(self, msg, title="Известие"):
        modal = js.document.getElementById("custom-alert")
        js.document.getElementById("alert-title").innerText = title
        js.document.getElementById("alert-message").innerText = msg
        modal.classList.remove("hidden")

    def save_room_state(self):
        if not self.current_room_name: return
        state = {
            "phase": self.phase, 
            "cards": self.cards, 
            "teams_state": self.teams_state, 
            "current_team_idx": self.current_team_idx, 
            "clue": self.clue, 
            "chats": self.chats, 
            "team_count": self.selected_team_count,
            "occupied_roles": self.occupied_roles
        }
        js.localStorage.setItem(f"codenames_room_{self.current_room_name}", json.dumps(state))
        js.localStorage.setItem("codenames_global_trigger", str(random.random()))

    def sync_from_storage(self):
        if self.phase == "LOBBY":
            self.refresh_rooms_list()
            return
        
        raw = js.localStorage.getItem(f"codenames_room_{self.current_room_name}")
        if not raw: return
        s = json.loads(raw)
        
        self.phase = s.get("phase", "ROLES")
        self.cards = s.get("cards", [])
        self.teams_state = s.get("teams_state", [])
        self.current_team_idx = s.get("current_team_idx", 0)
        self.clue = s.get("clue")
        self.chats = s.get("chats", {})
        self.selected_team_count = s.get("team_count", self.selected_team_count)
        self.occupied_roles = s.get("occupied_roles", {})
        
        if self.phase == "PLAYING" and self.player_team:
            self.render_game()
        else:
            self.show_role_selection()

    def show_lobby(self):
        self.phase, self.current_room_name, self.player_team, self.player_role = "LOBBY", "", None, None
        self.container.innerHTML = ""
        self.container.appendChild(js.document.getElementById("lobby-template").content.cloneNode(True))
        
        js.document.getElementById("player-name").value = self.player_name
        js.document.getElementById("create-room-btn").onclick = create_proxy(self.create_room)
        
        for btn in js.document.querySelectorAll(".team-opt-btn"):
            btn.onclick = create_proxy(self.on_team_opt_click)
        self.update_team_opt_ui()
        self.refresh_rooms_list()

    def on_team_opt_click(self, e):
        self.selected_team_count = int(e.currentTarget.getAttribute("data-value"))
        self.update_team_opt_ui()

    def update_team_opt_ui(self):
        for btn in js.document.querySelectorAll(".team-opt-btn"):
            val = int(btn.getAttribute("data-value"))
            if val == self.selected_team_count:
                btn.className = "team-opt-btn flex-1 py-2 rounded-lg border-2 border-blue-500 bg-blue-600 text-white text-xs shadow-md font-bold"
            else:
                btn.className = "team-opt-btn flex-1 py-2 rounded-lg border-2 border-slate-700 bg-slate-800 text-slate-400 text-xs hover:border-slate-500 font-bold"

    def refresh_rooms_list(self):
        list_el = js.document.getElementById("rooms-list")
        if not list_el: return
        reg = json.loads(js.localStorage.getItem("codenames_room_registry") or "[]")
        list_el.innerHTML = ""
        if not reg:
            list_el.innerHTML = '<p class="text-[10px] text-slate-500 italic text-center py-4">Няма открити активни игри...</p>'
            return
            
        for r in reg:
            btn = js.document.createElement("button")
            btn.className = "w-full flex justify-between items-center bg-slate-800 hover:bg-slate-700 p-4 rounded-xl border border-slate-700 text-xs mb-1 transition-all"
            t_count = r.get('team_count', 2)
            has_pass = " <i class='fas fa-lock text-amber-500 ml-2'></i>" if r.get('pass') else ""
            btn.innerHTML = f"<span><b class='text-blue-400'>{r['name']}</b>{has_pass} ({t_count} отбора)</span> <i class='fas fa-sign-in-alt text-blue-500'></i>"
            btn.onclick = create_proxy(lambda e, room=r: self.join_room(room))
            list_el.appendChild(btn)

    def create_room(self, e):
        name = js.document.getElementById("room-name").value.strip()
        p_name = js.document.getElementById("player-name").value.strip()
        pwd = js.document.getElementById("room-pass").value.strip()
        
        if not name or not p_name: 
            return self.show_alert("Моля, попълнете Вашето име и име на стая.")
        
        self.player_name = p_name
        js.localStorage.setItem("codenames_player_name", p_name)
        self.current_room_name = name
        self.phase = "ROLES"
        self.occupied_roles = {}
        
        reg = [r for r in json.loads(js.localStorage.getItem("codenames_room_registry") or "[]") if r['name'] != name]
        reg.append({"name": name, "team_count": self.selected_team_count, "pass": pwd})
        js.localStorage.setItem("codenames_room_registry", json.dumps(reg))
        
        self.save_room_state()
        self.show_role_selection()

    def join_room(self, r):
        p_name = js.document.getElementById("player-name").value.strip()
        if not p_name: 
            return self.show_alert("Въведете Вашето име първо.")
            
        if r.get('pass'):
            entered = js.prompt(f"Въведете парола за стая '{r['name']}':")
            if entered != r['pass']:
                return self.show_alert("Грешна парола!")
        
        self.player_name = p_name
        js.localStorage.setItem("codenames_player_name", p_name)
        self.current_room_name = r['name']
        self.selected_team_count = r.get('team_count', 2)
        self.phase = "ROLES"
        
        self.sync_from_storage()
        self.show_role_selection()

    def show_role_selection(self):
        self.container.innerHTML = ""
        self.container.appendChild(js.document.getElementById("role-selection-template").content.cloneNode(True))
        js.document.getElementById("room-title").innerText = f"Стая: {self.current_room_name}"
        js.document.getElementById("back-to-lobby").onclick = create_proxy(lambda e: self.show_lobby())
        
        grid = js.document.getElementById("teams-grid")
        if self.selected_team_count == 2: grid.className = "grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8"
        elif self.selected_team_count == 3: grid.className = "grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8"
        else: grid.className = "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
            
        for i in range(1, self.selected_team_count + 1):
            div = js.document.createElement("div")
            div.className = "bg-slate-900/50 p-6 rounded-3xl border border-slate-700 flex flex-col"
            div.innerHTML = f"<h4 class='font-bold mb-5 text-blue-400 uppercase tracking-widest text-xs'>Отбор {i}</h4>"
            
            for rid, rname in [('teller', 'Разказвач'), ('guesser', 'Познавач')]:
                role_key = f"{i}_{rid}"
                occupied_by = self.occupied_roles.get(role_key)
                
                btn = js.document.createElement("button")
                is_mine = (self.player_team == i and self.player_role == rid)
                
                if occupied_by and not is_mine:
                    btn.className = "w-full text-xs py-3 mb-2 rounded-xl font-bold border border-slate-700 bg-slate-800 text-slate-500 cursor-not-allowed flex items-center justify-center px-2"
                    btn.innerHTML = f"<i class='fas fa-user-circle mr-2 text-slate-600'></i> {occupied_by}"
                else:
                    bg_style = "bg-blue-600 border-blue-400 text-white shadow-lg ring-2 ring-blue-500/50" if is_mine else "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500 hover:bg-slate-750"
                    btn.className = f"w-full text-xs py-3 mb-2 rounded-xl font-bold border transition-all {bg_style}"
                    btn.innerText = rname
                    btn.onclick = create_proxy(lambda e, t=i, r=rid: self.claim_role(t, r))
                    
                div.appendChild(btn)
            grid.appendChild(div)
            
        start_btn = js.document.getElementById("start-game-btn")
        if self.player_team == 1 and self.player_role == 'teller' and self.phase != "PLAYING":
            start_btn.classList.remove("hidden")
            start_btn.innerText = "ГЕНЕРИРАЙ ДЪСКА"
            start_btn.onclick = create_proxy(lambda e: asyncio.ensure_future(self.init_board()))
        elif self.player_team is not None and self.phase == "PLAYING":
            start_btn.classList.remove("hidden")
            start_btn.innerText = "ВЛЕЗ В ИГРАТА"
            start_btn.onclick = create_proxy(lambda e: self.render_game())

    def claim_role(self, t, r):
        role_key = f"{t}_{r}"
        
        if self.player_team and self.player_role:
            old_key = f"{self.player_team}_{self.player_role}"
            if self.occupied_roles.get(old_key) == self.player_name:
                del self.occupied_roles[old_key]
        
        if role_key in self.occupied_roles and self.occupied_roles[role_key] != self.player_name:
            return self.show_alert("Тази роля вече е заета от друг играч.")
            
        self.player_team, self.player_role = t, r
        self.occupied_roles[role_key] = self.player_name
        self.save_room_state()
        
        if self.phase == "PLAYING":
            self.render_game()
        else:
            self.show_role_selection()

    async def init_board(self):
        self.container.innerHTML = """
        <div class='flex flex-col items-center justify-center h-full text-center p-10'>
            <div class='animate-spin h-14 w-14 border-4 border-blue-500 border-t-transparent rounded-full mb-8 shadow-xl shadow-blue-500/20'></div>
            <p class='text-2xl font-bold text-blue-400 mb-2'>Gemini AI Генерира Дъска...</p>
            <p class='text-slate-500 text-sm'>Създаване на 25 тематични думи и разпределяне на цветове...</p>
        </div>"""
        
        theme_input = js.document.getElementById("ai-theme")
        theme = theme_input.value if theme_input else ""
        prompt = f"Генерирай JSON масив от 25 уникални български съществителни думи. {'Тема: ' + theme if theme else 'Темата може да е произволна.'} Върни само и единствено JSON масива."
        
        try:
            res_text = await js.window.callGemini(prompt)
            game_words = json.loads(res_text) if res_text else random.sample(DEFAULT_WORDS, 25)
            if len(game_words) < 25: game_words = random.sample(DEFAULT_WORDS, 25)
        except:
            game_words = random.sample(DEFAULT_WORDS, 25)

        self.teams_state, self.chats = [], {}
        colors = [TeamColor.GREEN, TeamColor.RED, TeamColor.BLUE, TeamColor.YELLOW]
        
        for i in range(self.selected_team_count):
            self.teams_state.append({"id": i+1, "color": colors[i], "score": 0, "name": f"Отбор {i+1}"})
            self.chats[str(i+1)] = []
            
        indices = list(range(25))
        random.shuffle(indices)
        assignments = [TeamColor.NEUTRAL] * 25
        
        ptr = 0
        self.words_per_team = 8 if self.selected_team_count == 2 else 6
        for t in self.teams_state:
            for _ in range(self.words_per_team):
                assignments[indices[ptr]] = t['color']
                ptr += 1
        
        assignments[indices[ptr]] = TeamColor.BOMB
        
        self.cards = [{"id": i, "word": game_words[i], "assignment": assignments[i], "revealed": False} for i in range(25)]
        self.phase, self.current_team_idx, self.clue = "PLAYING", 0, None
        self.save_room_state()
        self.render_game()

    def render_game(self):
        if not self.teams_state: 
            self.sync_from_storage()
            return
            
        ct = self.teams_state[self.current_team_idx]
        theme = TEAM_THEMES[ct['color']]
        
        html = f"""
        <div class="flex h-full gap-4 overflow-hidden animate-in fade-in">
            <div class="flex-[3] flex flex-col h-full overflow-hidden">
                <header class="flex justify-between items-center bg-slate-800 p-3 rounded-2xl border border-slate-700 mb-3 shadow-lg">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-xl {theme.split(' ')[0]} flex items-center justify-center shadow-lg"><i class="fas fa-shield-alt text-white"></i></div>
                        <div><h2 class="font-bold text-sm">{ct['name']}</h2><p class="text-[9px] text-slate-400 uppercase tracking-widest font-bold">{'ВАШ ХОД' if (self.current_team_idx + 1) == self.player_team else 'ИЗЧАКВАНЕ'}</p></div>
                    </div>
                    <div class="flex items-center gap-4">
                        <div class="flex gap-2">"""
        
        for t in self.teams_state:
            t_col = TEAM_THEMES[t['color']].split(' ')[0]
            html += f"""<div class="flex flex-col items-center">
                            <span class="text-[8px] font-bold text-slate-500 mb-0.5">O{t['id']}</span>
                            <div class="px-3 py-1 rounded-lg {t_col} text-xs font-bold text-white shadow-sm">{t['score']}/{self.words_per_team}</div>
                        </div>"""
                            
        html += """</div><button id="exit-game" class="text-slate-500 hover:text-red-400 p-2 transition-all"><i class="fas fa-sign-out-alt"></i></button></div></header>
                <div class="flex-1 grid grid-cols-5 gap-2 overflow-y-auto custom-scrollbar pr-1">"""
                
        for c in self.cards:
            rev = c['revealed']
            show_color = rev or self.player_role == 'teller'
            ctheme = TEAM_THEMES[c['assignment']] if show_color else "bg-slate-800 border-slate-700 text-slate-400"
            is_clickable = self.player_role == 'guesser' and not rev and self.clue and (self.current_team_idx + 1) == self.player_team
            
            html += f"""<div class="card-btn relative aspect-square rounded-2xl border-2 {ctheme} {'opacity-60 grayscale-[0.3]' if rev else 'hover:scale-[1.02] hover:shadow-xl'} overflow-hidden {'cursor-pointer' if is_clickable else 'cursor-default'} flex items-center justify-center p-2 transition-all" data-id="{c['id']}">
                        <h3 class="relative z-10 font-bold text-[10px] sm:text-xs text-center uppercase tracking-tighter leading-none">{c['word']}</h3>
                        { '<div class="absolute bottom-1 right-1 opacity-20 text-[8px]"><i class="fas fa-check-circle"></i></div>' if rev else '' }
                    </div>"""
                    
        html += """</div><div class="mt-3 bg-slate-800 p-4 rounded-3xl border border-slate-700 shadow-xl">"""
        
        if (self.current_team_idx + 1) == self.player_team:
            if self.player_role == 'teller' and not self.clue:
                html += '<div class="flex gap-3"><input id="clue-in" class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-blue-500" placeholder="Подсказка (напр: ПЛОД 3)"><button id="send-clue" class="bg-blue-600 hover:bg-blue-500 px-8 py-3 rounded-xl font-bold text-sm shadow-lg shadow-blue-500/20">ИЗПРАТИ</button></div>'
            elif self.player_role == 'guesser' and self.clue:
                html += f'<div class="flex justify-between items-center"><div><span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">ПОДСКАЗКА:</span> <span class="text-xl font-black text-blue-400 tracking-widest ml-4">{self.clue}</span></div><button id="pass-turn" class="bg-slate-700 hover:bg-slate-600 px-8 py-3 rounded-xl text-sm font-bold shadow-lg">КРАЙ ХОД</button></div>'
            else: html += f"<p class='text-center text-slate-500 italic text-sm font-bold py-1 animate-pulse'>Чакайте партньора си...</p>"
        else:
            clue_txt = f"ПОДСКАЗКА: <span class='text-blue-400 font-bold ml-2'>{self.clue}</span>" if self.clue else "Изчакване на подсказка..."
            html += f"<div class='text-center py-2'><span class='text-slate-500 text-[10px] font-bold uppercase mr-3'>Отбор {self.current_team_idx + 1} в действие:</span> <span class='text-sm italic text-slate-300'>{clue_txt}</span></div>"
            
        team_id_str = str(self.player_team)
        html += f"""</div></div><div class="flex-1 flex flex-col h-full bg-slate-800/40 rounded-3xl border border-slate-700 overflow-hidden shadow-2xl">
                <div class="p-4 border-b border-slate-700 bg-slate-800/60 flex justify-between items-center"><h3 class="font-bold text-[10px] uppercase text-slate-400 flex items-center gap-2"><i class="fas fa-comments text-blue-500"></i> Чат Отбор {team_id_str}</h3> <span class="text-[8px] bg-slate-700 px-2 py-0.5 rounded-full text-slate-400 font-bold">LIVE</span></div>
                <div id="chat-msgs" class="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar bg-slate-900/10">"""
        
        for m in self.chats.get(team_id_str, []):
            is_me = m['u'] == self.player_name
            align, bubble = ("text-right", "bg-blue-600/10 border-blue-500/20") if is_me else ("text-left", "bg-slate-700/40 border-slate-600")
            html += f'<div class="{align} chat-msg"><span class="text-[8px] font-bold text-slate-500 uppercase mb-1 block">{m["u"]} • {m["t"]}</span><div class="inline-block max-w-[90%] {bubble} border px-3 py-2 text-xs text-slate-200 shadow-sm rounded-2xl">{m["m"]}</div></div>'
            
        html += """</div><div class="p-3 bg-slate-800/80 border-t border-slate-700"><div class="flex gap-2"><input id="chat-in" class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-xs outline-none focus:ring-1 focus:ring-blue-500" placeholder="Напишете нещо..."><button id="chat-send" class="bg-blue-600 hover:bg-blue-500 p-2.5 rounded-xl transition-all shadow-md"><i class="fas fa-paper-plane text-xs"></i></button></div></div></div></div>"""
        
        self.container.innerHTML = html
        js.document.getElementById("exit-game").onclick = create_proxy(lambda e: self.show_lobby())
        js.document.getElementById("chat-send").onclick = create_proxy(self.send_message)
        for el in js.document.querySelectorAll(".card-btn"): el.onclick = create_proxy(self.handle_card_click)
        if js.document.getElementById("send-clue"): js.document.getElementById("send-clue").onclick = create_proxy(self.submit_clue)
        if js.document.getElementById("pass-turn"): js.document.getElementById("pass-turn").onclick = create_proxy(lambda e: self.next_turn())
        chat_div = js.document.getElementById("chat-msgs")
        if chat_div: chat_div.scrollTop = chat_div.scrollHeight

    def send_message(self, e):
        inp = js.document.getElementById("chat-in"); txt = inp.value.strip()
        if not txt: return
        self.chats[str(self.player_team)].append({"u": self.player_name, "m": txt, "t": datetime.now().strftime("%H:%M")})
        inp.value = ""; self.save_room_state(); self.render_game()

    def submit_clue(self, e):
        val = js.document.getElementById("clue-in").value.strip()
        if not val: return
        self.clue = val; self.save_room_state(); self.render_game()

    def handle_card_click(self, e):
        if self.player_role != 'guesser' or not self.clue or (self.current_team_idx + 1) != self.player_team: return
        c_id = int(e.currentTarget.getAttribute("data-id"))
        card = self.cards[c_id]
        if card['revealed']: return
        card['revealed'] = True
        my_color = self.teams_state[self.current_team_idx]['color']
        if card['assignment'] == TeamColor.BOMB: self.show_alert("БОМБА! Вашият отбор загуби играта!", "КРАЙ"); self.next_turn()
        elif card['assignment'] == my_color:
            self.teams_state[self.current_team_idx]['score'] += 1
            if self.teams_state[self.current_team_idx]['score'] >= self.words_per_team: self.show_alert("ПОБЕДА! Познахте всички думи!", "ПОЗДРАВЛЕНИЯ")
            self.save_room_state(); self.render_game()
        else: self.next_turn()

    def next_turn(self):
        self.current_team_idx = (self.current_team_idx + 1) % len(self.teams_state)
        self.clue = None; self.save_room_state(); self.render_game()

GameManager()
