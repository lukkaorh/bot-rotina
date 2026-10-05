"""
Bot de mensagens automáticas - L.R. VALEN editora
Usa a API oficial da Meta (Graph API). Responde apenas a quem
comentou ou mandou mensagem para a página.

Instalação:
    pip install flask requests

Variáveis de ambiente (nunca coloque tokens direto no código):
    PAGE_ACCESS_TOKEN  -> token da página (Meta for Developers)
    VERIFY_TOKEN       -> uma senha qualquer que você inventa
    LINK_PRODUTO       -> link de venda do Rotina Clara

Execução:
    python bot_rotina_clara.py
(para receber webhooks, a URL precisa ser pública e HTTPS;
 em testes use ngrok ou um serviço como Render/Railway)
"""
import os
import requests
from flask import Flask, request

app = Flask(__name__)

PAGE_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "troque-esta-senha")
LINK = os.environ.get("LINK_PRODUTO", "https://seu-link-aqui")
API = "https://graph.facebook.com/v21.0"

PALAVRA_GATILHO = "rotina"

MSG_BOAS_VINDAS = (
    "Oi! Que bom ter você por aqui 😊\n\n"
    "Aqui está o Rotina Clara, com preço de lançamento de R$ 14,90:\n"
    f"{LINK}\n\n"
    "Se tiver dúvidas, responda com uma destas palavras:\n"
    "• PREÇO\n• COMO RECEBO\n• SUPORTE"
)

RESPOSTAS = {
    "preço": f"O Rotina Clara está em lançamento por R$ 14,90. Garanta aqui: {LINK}",
    "preco": f"O Rotina Clara está em lançamento por R$ 14,90. Garanta aqui: {LINK}",
    "como recebo": "Depois da compra, o acesso chega no e-mail cadastrado, em poucos minutos.",
    "suporte": "Sem problema! Escreva sua dúvida aqui que a nossa equipe responde em breve.",
}


def enviar_mensagem(psid, texto):
    """Envia mensagem para quem já conversou com a página (janela de 24h)."""
    r = requests.post(
        f"{API}/me/messages",
        params={"access_token": PAGE_TOKEN},
        json={
            "recipient": {"id": psid},
            "message": {"text": texto},
            "messaging_type": "RESPONSE",
        },
        timeout=15,
    )
    print("mensagem:", r.status_code, r.text[:200])


def resposta_privada(comment_id, texto):
    """Manda DM para quem comentou (uma por comentário, até 7 dias)."""
    r = requests.post(
        f"{API}/{comment_id}/private_replies",
        params={"access_token": PAGE_TOKEN},
        json={"message": texto},
        timeout=15,
    )
    print("private reply:", r.status_code, r.text[:200])


def responder_comentario(comment_id, texto):
    r = requests.post(
        f"{API}/{comment_id}/comments",
        params={"access_token": PAGE_TOKEN},
        json={"message": texto},
        timeout=15,
    )
    print("comentário:", r.status_code, r.text[:200])


@app.route("/webhook", methods=["GET"])
def verificar():
    """A Meta chama isto uma vez para validar seu webhook."""
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge", ""), 200
    return "token inválido", 403


@app.route("/webhook", methods=["POST"])
def receber():
    dados = request.get_json(silent=True) or {}
    print("EVENTO RECEBIDO:", str(dados)[:800], flush=True)

    for entrada in dados.get("entry", []):
        # 1) Mensagens enviadas para a página
        for evento in entrada.get("messaging", []):
            msg = evento.get("message", {})
            if msg.get("is_echo") or "text" not in msg:
                continue
            psid = evento["sender"]["id"]
            texto = msg["text"].strip().lower()
            resposta = next(
                (v for k, v in RESPOSTAS.items() if k in texto), MSG_BOAS_VINDAS
            )
            enviar_mensagem(psid, resposta)

        # 2) Comentários nos posts da página
        for mudanca in entrada.get("changes", []):
            valor = mudanca.get("value", {})
            if mudanca.get("field") != "feed":
                print("IGNORADO: campo", mudanca.get("field"), flush=True)
                continue
            if valor.get("item") != "comment" or valor.get("verb") != "add":
                print("IGNORADO: item/verb", valor.get("item"), valor.get("verb"), flush=True)
                continue
            # ignora comentários feitos pela própria página
            if valor.get("from", {}).get("id") == entrada.get("id"):
                print("IGNORADO: comentário feito pela própria página", flush=True)
                continue
            if PALAVRA_GATILHO in valor.get("message", "").lower():
                cid = valor["comment_id"]
                print("COMENTÁRIO COM GATILHO:", cid, flush=True)
                responder_comentario(cid, "Te enviei os detalhes na sua caixa de mensagens! 📩")
                resposta_privada(cid, MSG_BOAS_VINDAS)
            else:
                print("IGNORADO: sem a palavra gatilho:", valor.get("message"), flush=True)

    return "ok", 200


if __name__ == "__main__":
    app.run(port=5000)
