import random
from pyswip import Prolog
import time

class MundoPitfall:
    def __init__(self):
        self.tamanho = 12
        self.mapa = [['Vazio' for _ in range(self.tamanho)] for _ in range(self.tamanho)]
        self.energia = 100
        self.pontuacao = 0
        self.posicao_agente = (1, 1) # (X, Y) - Usando 1-index para bater com Prolog
        self.jogo_ativo = True
        self.ouro_coletado = 0
        
        self.prolog = Prolog()
        self.prolog.consult("agente.pl")
        self._inicializar_prolog()
        self.gerar_elementos_aleatorios()

    def _inicializar_prolog(self):
        # Limpa o conhecimento anterior
        list(self.prolog.query("retractall(visitado(_,_))"))
        list(self.prolog.query("retractall(tem_brisa(_,_))"))
        list(self.prolog.query("retractall(tem_passos(_,_))"))
        list(self.prolog.query("retractall(tem_flash(_,_))"))
        list(self.prolog.query("retractall(brilho(_,_))"))
        list(self.prolog.query("retractall(posicao_atual(_,_))"))
        
        # Posição inicial
        self.atualizar_posicao_prolog(1, 1)
        self.prolog.assertz("visitado(1, 1)")

    def atualizar_posicao_prolog(self, x, y):
        list(self.prolog.query("retractall(posicao_atual(_,_))"))
        self.prolog.assertz(f"posicao_atual({x}, {y})")

    def gerar_elementos_aleatorios(self):
        # Sorteia as posições conforme as restrições do PDF
        elementos = (
            ['Inimigo_20'] * 2 + 
            ['Inimigo_50'] * 2 + 
            ['Poco'] * 8 + 
            ['Ouro'] * 3 + 
            ['Morcego'] * 4 +
            ['PowerUp'] * 3
        )
        
        for elemento in elementos:
            while True:
                # Sorteia de 1 a 12
                x, y = random.randint(1, 12), random.randint(1, 12)
                # Não pode nascer na posição inicial/saída (1,1) e deve ser espaço vazio
                if (x, y) != (1, 1) and self.mapa[x-1][y-1] == 'Vazio':
                    self.mapa[x-1][y-1] = elemento
                    break

    def perceber_ambiente(self, x, y):
        px, py = x - 1, y - 1
        adjacentes = [(px+1, py), (px-1, py), (px, py+1), (px, py-1)]
        
        brisa = passos = flash = False
        
        if self.mapa[px][py] == 'Ouro':
            self.prolog.assertz(f"brilho({x}, {y})")
            
        for ax, ay in adjacentes:
            if 0 <= ax < self.tamanho and 0 <= ay < self.tamanho:
                vizinho = self.mapa[ax][ay]
                if vizinho == 'Poco': brisa = True
                if vizinho in ['Inimigo_20', 'Inimigo_50']: passos = True
                if vizinho == 'Morcego': flash = True

        if brisa: self.prolog.assertz(f"tem_brisa({x}, {y})")
        if passos: self.prolog.assertz(f"tem_passos({x}, {y})")
        if flash: self.prolog.assertz(f"tem_flash({x}, {y})")

    def aplicar_regras_sala(self, x, y):
        sala = self.mapa[x-1][y-1]
        
        if sala == 'Poco':
            self.pontuacao -= 1000
            print("☠️ Você caiu em um poço! Game Over.")
            self.jogo_ativo = False
            
        elif sala == 'Inimigo_20':
            self.energia -= 20
            print("⚔️ Você tomou 20 de dano de um monstro pequeno!")
            
        elif sala == 'Inimigo_50':
            self.energia -= 50
            print("⚔️ Você tomou 50 de dano de um monstro grande!")
            
        elif sala == 'Morcego':
            print("🦇 Um morcego te pegou! Teletransportando...")
            nx, ny = random.randint(1, 12), random.randint(1, 12)
            self.posicao_agente = (nx, ny)
            self.atualizar_posicao_prolog(nx, ny)
            self.aplicar_regras_sala(nx, ny) # Pode cair em outro perigo
            return # Evita continuar o fluxo normal
            
        elif sala == 'PowerUp':
            self.energia += 20
            self.mapa[x-1][y-1] = 'Vazio'
            print("🔋 Você pegou um PowerUp! +20 de Energia.")

        if self.energia <= 0:
            self.pontuacao -= 1000
            print("☠️ Você ficou sem energia e morreu! Game Over.")
            self.jogo_ativo = False

    def jogar_turno(self):
        x, y = self.posicao_agente
        print(f"\n--- Turno --- Posição Atual: [{x}, {y}] | Energia: {self.energia} | Pontos: {self.pontuacao}")
        
        # 1. Agente percebe o ambiente e anota no Prolog
        self.perceber_ambiente(x, y)
        self.prolog.assertz(f"visitado({x}, {y})")
        
        # Condição de vitória (retornar para 1,1 após pegar ouros)
        if (x, y) == (1, 1) and self.ouro_coletado == 3:
            print("🎉 Você escapou com vida e com todos os tesouros! Vitória!")
            self.jogo_ativo = False
            return

        # 2. Prolog decide a ação
        resultado = list(self.prolog.query("decidir_acao(Acao)"))
        
        if not resultado:
            print("O agente está encurralado e não sabe o que fazer. Fim.")
            self.jogo_ativo = False
            return
            
        acao = resultado[0]["Acao"]
        
        # 3. Executa a ação
        if acao == "pegar":
            print("💰 Pegou ouro! (+1000 pontos)")
            self.pontuacao += 1000
            self.ouro_coletado += 1
            self.mapa[x-1][y-1] = 'Vazio' # Remove o ouro
            list(self.prolog.query(f"retract(brilho({x}, {y}))"))
            
        elif isinstance(acao, str) and acao == "usar_a_estrela":
            # Aqui você deve integrar a chamada do A* do código de exemplo do professor
            # O A* deve buscar a coordenada (X,Y) mais próxima onde seguro(X,Y) seja verdadeiro.
            print("🔍 Nenhuma sala adjacente é 100% segura. Precisamos acionar o algoritmo A* (Implementar integração visual).")
            self.jogo_ativo = False # Parando aqui apenas por demonstração
            
        else: # Mover
            # Ação vem como um termo do tipo 'mover_adjacente(2, 1)' do pyswip. 
            # Como é um Functor no PySwip, extraímos os argumentos:
            nx, ny = acao.args[0], acao.args[1]
            print(f"🚶 Agente decidiu se mover para [{nx}, {ny}] (Custo: -1)")
            self.pontuacao -= 1
            self.posicao_agente = (nx, ny)
            self.atualizar_posicao_prolog(nx, ny)
            self.aplicar_regras_sala(nx, ny)

    def executar(self):
        while self.jogo_ativo:
            self.jogar_turno()
            time.sleep(1) # Pausa para conseguir acompanhar no terminal
        print(f"\nFIM DE JOGO. Pontuação Final: {self.pontuacao}")

if __name__ == "__main__":
    jogo = MundoPitfall()
    jogo.executar()