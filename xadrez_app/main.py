import chess
import chess.engine
import threading
import os
import sys
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.utils import get_color_from_hex

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class ChessGameWidget(BoxLayout):
    def __init__(self, **kwargs):
        super(ChessGameWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10

        self.board = chess.Board()
        self.botoes = {}
        
        self.estado = {
            "selected_sq": None,
            "last_move": None,
            "ia_ativa": True,
            "cor_ia": chess.BLACK,
            "board_flipped": False,
            "ia_pensando": False,
            "engine": None
        }

        self.pecas_unicode = {
            "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
            "p": "♙", "n": "♘", "b": "♗", "r": "♖", "q": "♕", "k": "♔",
        }

        # --- UI Components ---
        self.texto_estado = Label(
            text="Carregando motor...", 
            font_size=20, 
            bold=True, 
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.texto_estado)

        # Tabuleiro UI (Grid 8x8)
        self.tabuleiro_ui = GridLayout(cols=8, rows=8, size_hint=(None, None), width=360, height=360)
        # Centralizar o tabuleiro
        board_container = BoxLayout(orientation='horizontal', size_hint=(1, None), height=360)
        board_container.add_widget(BoxLayout(size_hint_x=1)) # Espaçador esquerdo
        board_container.add_widget(self.tabuleiro_ui)
        board_container.add_widget(BoxLayout(size_hint_x=1)) # Espaçador direito
        self.add_widget(board_container)

        for r in range(8):
            for c in range(8):
                btn = Button(
                    text="",
                    font_size=28,
                    bold=True,
                    background_normal="",
                    background_down=""
                )
                btn.bind(on_release=lambda instance, row=r, col=c: self.on_square_click(row, col))
                self.botoes[(r, c)] = btn
                self.tabuleiro_ui.add_widget(btn)

        # Botões de Ação
        row_botoes_1 = BoxLayout(size_hint=(1, None), height=50, spacing=10)
        self.btn_nova_partida = Button(text="Nova Partida", bold=True, background_color=get_color_from_hex("#3498DB"))
        self.btn_nova_partida.bind(on_release=self.abrir_dialogo_nova_partida)
        
        self.btn_ia = Button(text="Modo: Automático", bold=True, background_color=get_color_from_hex("#A9DFBF"), color=(0,0,0,1))
        self.btn_ia.bind(on_release=self.toggle_ia)
        
        row_botoes_1.add_widget(self.btn_nova_partida)
        row_botoes_1.add_widget(self.btn_ia)
        self.add_widget(row_botoes_1)

        row_botoes_2 = BoxLayout(size_hint=(1, None), height=50, spacing=10)
        self.btn_undo = Button(text="Desfazer jogada", bold=True, background_color=get_color_from_hex("#D6EAF8"), color=(0,0,0,1))
        self.btn_undo.bind(on_release=self.desfazer_jogada)
        
        self.btn_flip = Button(text="Girar Tabuleiro", bold=True, background_color=get_color_from_hex("#F9E79F"), color=(0,0,0,1))
        self.btn_flip.bind(on_release=self.inverter_tabuleiro)
        
        row_botoes_2.add_widget(self.btn_undo)
        row_botoes_2.add_widget(self.btn_flip)
        self.add_widget(row_botoes_2)

        # Histórico
        self.add_widget(Label(text="Histórico:", bold=True, color=(0,0,0,1), size_hint_y=None, height=30))
        
        self.texto_historico = Label(text="", color=(0,0,0,1), font_size=14, halign="left", valign="top")
        self.texto_historico.bind(size=self.texto_historico.setter('text_size'))
        
        scroll = ScrollView(size_hint=(1, None), height=90)
        scroll.add_widget(self.texto_historico)
        
        hist_container = BoxLayout(size_hint=(1, None), height=100, padding=5)
        hist_container.add_widget(scroll)
        self.add_widget(hist_container)

        # Inicialização
        Clock.schedule_once(lambda dt: self.abrir_dialogo_nova_partida(), 0.5)
        self.atualizar_tabuleiro()
        threading.Thread(target=self.iniciar_motor, daemon=True).start()

    def atualizar_tabuleiro(self, *args):
        for r in range(8):
            for c in range(8):
                if self.estado["board_flipped"]:
                    sq = chess.square(7 - c, r)
                else:
                    sq = chess.square(c, 7 - r)
                
                piece = self.board.piece_at(sq)
                is_light_sq = (r + c) % 2 == 0
                
                # Cores idênticas ao projeto anterior
                hex_color = "#FFCE9E" if is_light_sq else "#D18B47"
                
                if self.estado["last_move"] and sq in (self.estado["last_move"].from_square, self.estado["last_move"].to_square):
                    hex_color = "#F7F769" if is_light_sq else "#BBCB45"
                
                if self.estado["selected_sq"] == sq:
                    hex_color = "#BACA44"
                
                btn = self.botoes[(r, c)]
                btn.background_color = get_color_from_hex(hex_color)
                
                if piece:
                    btn.text = self.pecas_unicode[piece.symbol()]
                    btn.color = (1, 1, 1, 1) if piece.color == chess.WHITE else (0, 0, 0, 1)
                else:
                    btn.text = ""

        if self.board.is_game_over():
            self.texto_estado.text = "Fim de jogo!"
        else:
            if self.estado["ia_pensando"]:
                self.texto_estado.text = "Xadrista está a pensar..."
            else:
                vez = "Brancas" if self.board.turn == chess.WHITE else "Pretas"
                self.texto_estado.text = f"Sua vez! ({vez})"

    def registrar_lance(self, move):
        san = self.board.san(move)
        if self.board.turn == chess.WHITE:
            numero_jogada = self.board.fullmove_number
            self.texto_historico.text += f"{numero_jogada}. {san} "
        else:
            self.texto_historico.text += f"{san}\n"

    def reconstruir_historico(self):
        self.texto_historico.text = ""
        replay = chess.Board()
        for move in self.board.move_stack:
            san = replay.san(move)
            if replay.turn == chess.WHITE:
                self.texto_historico.text += f"{replay.fullmove_number}. {san} "
            else:
                self.texto_historico.text += f"{san}\n"
            replay.push(move)

    def desfazer_jogada(self, instance):
        if self.estado["ia_pensando"] or not self.board.move_stack:
            return
        self.estado["selected_sq"] = None
        self.board.pop()
        if self.estado["ia_ativa"] and self.board.turn == self.estado["cor_ia"] and self.board.move_stack:
            self.board.pop()
        self.estado["last_move"] = self.board.peek() if self.board.move_stack else None
        self.reconstruir_historico()
        self.atualizar_tabuleiro()

    def inverter_tabuleiro(self, instance):
        self.estado["board_flipped"] = not self.estado["board_flipped"]
        self.atualizar_tabuleiro()

    def toggle_ia(self, instance):
        self.estado["ia_ativa"] = not self.estado["ia_ativa"]
        if self.estado["ia_ativa"]:
            self.btn_ia.text = "Modo: Automático"
            self.btn_ia.background_color = get_color_from_hex("#A9DFBF")
            if self.board.turn == self.estado["cor_ia"]:
                self.solicitar_jogada_ia()
        else:
            self.btn_ia.text = "Modo: Manual"
            self.btn_ia.background_color = get_color_from_hex("#F5B7B1")

    def solicitar_jogada_ia(self):
        if self.estado["ia_pensando"] or not self.estado["engine"] or self.board.is_game_over():
            return
        self.estado["ia_pensando"] = True
        Clock.schedule_once(self.atualizar_tabuleiro, 0)
        threading.Thread(target=self.jogada_ia, daemon=True).start()

    def jogada_ia(self):
        try:
            fen = self.board.fen()
            board_calculo = chess.Board(fen)
            resultado = self.estado["engine"].play(board_calculo, chess.engine.Limit(time=1.5))
            
            def aplicar(dt):
                if self.board.fen() != fen:
                    self.estado["ia_pensando"] = False
                    return
                move = resultado.move
                if move in self.board.legal_moves:
                    self.registrar_lance(move)
                    self.board.push(move)
                    self.estado["last_nomve"] = move
                    self.estado["last_move"] = move
                self.estado["ia_pensando"] = False
                self.atualizar_tabuleiro()
            
            Clock.schedule_once(aplicar, 0)
        except Exception as e:
            print("Erro IA:", e)
            self.estado["ia_pensando"] = False
            Clock.schedule_once(self.atualizar_tabuleiro, 0)

    def on_square_click(self, r, c):
        if self.board.is_game_over() or self.estado["ia_pensando"]:
            return
        if self.estado["ia_ativa"] and self.board.turn == self.estado["cor_ia"]:
            return

        if self.estado["board_flipped"]:
            sq = chess.square(7 - c, r)
        else:
            sq = chess.square(c, 7 - r)

        if self.estado["selected_sq"] is None:
            piece = self.board.piece_at(sq)
            if piece and piece.color == self.board.turn:
                self.estado["selected_sq"] = sq
        else:
            move = chess.Move(self.estado["selected_sq"], sq)
            piece = self.board.piece_at(self.estado["selected_sq"])
            if piece and piece.piece_type == chess.PAWN and chess.square_rank(sq) in [0, 7]:
                move = chess.Move(self.estado["selected_sq"], sq, promotion=chess.QUEEN)

            if move in self.board.legal_moves:
                self.registrar_lance(move)
                self.board.push(move)
                self.estado["last_move"] = move
                self.estado["selected_sq"] = None
                self.atualizar_tabuleiro()

                if self.estado["ia_ativa"] and self.board.turn == self.estado["cor_ia"]:
                    self.solicitar_jogada_ia()
            else:
                piece_click = self.board.piece_at(sq)
                if piece_click and piece_click.color == self.board.turn:
                    self.estado["selected_sq"] = sq
                else:
                    self.estado["selected_sq"] = None
        
        self.atualizar_tabuleiro()

    def escolher_cor(self, cor_adversario, popup):
        popup.dismiss()
        self.board.reset()
        self.estado["selected_sq"] = None
        self.estado["last_move"] = None
        
        self.estado["cor_ia"] = cor_adversario
        self.estado["board_flipped"] = (cor_adversario == chess.WHITE)
        self.estado["ia_ativa"] = True
        
        self.btn_ia.text = "Modo: Automático"
        self.btn_ia.background_color = get_color_from_hex("#A9DFBF")
        self.texto_historico.text = ""
        
        self.atualizar_tabuleiro()
        
        if self.estado["ia_ativa"] and self.board.turn == self.estado["cor_ia"]:
            self.solicitar_jogada_ia()

    def abrir_dialogo_nova_partida(self, *args):
        conteudo = BoxLayout(orientation='vertical', spacing=10, padding=20)
        conteudo.add_widget(Label(text="Com quais peças você quer começar?", bold=True, color=(0,0,0,1)))
        
        btn_brancas = Button(text="Brancas", bold=True, background_color=get_color_from_hex("#FAE1C8"), color=(0,0,0,1))
        btn_pretas = Button(text="Pretas", bold=True, background_color=get_color_from_hex("#CD7A27"), color=(1,1,1,1))
        
        popup = Popup(
            title="Opções de Nova Partida",
            content=conteudo,
            size_hint=(None, None),
            size=(300, 220),
            auto_dismiss=False
        )
        
        btn_brancas.bind(on_release=lambda x: self.escolher_cor(chess.WHITE, popup))
        btn_pretas.bind(on_release=lambda x: self.escolher_cor(chess.BLACK, popup))
        
        conteudo.add_widget(btn_brancas)
        conteudo.add_widget(btn_pretas)
        popup.open()

    def iniciar_motor(self):
        caminho = resource_path("stockfish.exe")
        try:
            self.estado["engine"] = chess.engine.SimpleEngine.popen_uci(caminho)
            self.estado["engine"].configure({"Skill Level": 14})
            
            if self.estado["ia_ativa"] and self.board.turn == self.estado["cor_ia"]:
                self.solicitar_jogada_ia()
            else:
                Clock.schedule_once(self.atualizar_tabuleiro, 0)
        except Exception as e:
            def erro_ui(dt):
                self.texto_estado.text = "Erro: Motor Stockfish não encontrado."
            Clock.schedule_once(erro_ui, 0)
            print(f"Erro ao carregar motor: {e}")

class XadrezApp(App):
    def build(self):
        self.title = "Xadrez"
        return ChessGameWidget()

if __name__ == '__main__':
    XadrezApp().run()