from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
import chess
import urllib.request
import json
import threading
import random

class TabuleiroXadrez(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 8
        self.board = chess.Board()
        self.casa_selecionada = None
        self.botoes = {}
        
        self.simbolos = {
            'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
            'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
        }
        self.criar_tabuleiro()

    def criar_tabuleiro(self):
        for linha in range(7, -1, -1):
            for coluna in range(8):
                quadrado = chess.square(coluna, linha)
                cor_fundo = [0.82, 0.55, 0.28, 1] if (linha + coluna) % 2 == 0 else [0.98, 0.82, 0.6, 1]
                
                btn = Button(
                    text='',
                    font_size='32sp',
                    background_normal='',
                    background_color=cor_fundo
                )
                btn.quadrado = quadrado
                btn.bind(on_press=self.clique_casa)
                self.add_widget(btn)
                self.botoes[quadrado] = btn
        self.atualizar_interface()

    def atualizar_interface(self):
        for quadrado, btn in self.botoes.items():
            peca = self.board.piece_at(quadrado)
            btn.text = self.simbolos.get(peca.symbol(), "") if peca else ""
            
            linha = chess.square_rank(quadrado)
            coluna = chess.square_file(quadrado)
            if self.casa_selecionada == quadrado:
                btn.background_color = [1, 0.8, 0.2, 1]
            else:
                btn.background_color = [0.82, 0.55, 0.28, 1] if (linha + coluna) % 2 == 0 else [0.98, 0.82, 0.6, 1]

    def clique_casa(self, instance):
        quadrado = instance.quadrado
        if self.casa_selecionada is None:
            peca = self.board.piece_at(quadrado)
            if peca and peca.color == chess.WHITE:
                self.casa_selecionada = quadrado
                self.atualizar_interface()
        else:
            movimento = chess.Move(self.casa_selecionada, quadrado)
            peca = self.board.piece_at(self.casa_selecionada)
            if peca and peca.piece_type == chess.PAWN and chess.square_rank(quadrado) == 7:
                movimento = chess.Move(self.casa_selecionada, quadrado, promotion=chess.QUEEN)

            if movimento in self.board.legal_moves:
                self.board.push(movimento)
                self.casa_selecionada = None
                self.atualizar_interface()
                threading.Thread(target=self.jogada_ia_thread).start()
            else:
                peca = self.board.piece_at(quadrado)
                if peca and peca.color == chess.WHITE:
                    self.casa_selecionada = quadrado
                else:
                    self.casa_selecionada = None
                self.atualizar_interface()

    def jogada_ia_thread(self):
        if self.board.is_game_over():
            return

        fen = self.board.fen().replace(' ', '%20')
        url = f"https://stockfish.online/api/s/v2.php?fen={fen}&depth=10"
        
        movimento_final = None
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                dados = json.loads(response.read().decode())
                if dados.get("success"):
                    movimento_final = chess.Move.from_uci(dados["bestmove"].split()[1])
        except Exception:
            pass

        if not movimento_final:
            movimentos = list(self.board.legal_moves)
            if movimentos:
                movimento_final = random.choice(movimentos)

        if movimento_final:
            self.board.push(movimento_final)
            Clock.schedule_once(lambda dt: self.atualizar_interface())

class XadrezApp(App):
    def build(self):
        return TabuleiroXadrez()

if __name__ == '__main__':
    XadrezApp().run()