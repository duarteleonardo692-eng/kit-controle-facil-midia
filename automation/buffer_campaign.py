#!/usr/bin/env python3
"""Campanha programada: posts inéditos, a cada 10min, com estado persistente.
Não altera publicações antigas e não usa Metricool.
"""
import json
import os
import struct
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from buffer_publish import (
    EXPECTED_CHANNELS, REPO, fetch_posts, gql_string, is_duplicate,
    locate_channels, query_graphql,
)

DATA = Path("automation/campanha-03nov.json")
STATE = Path("automation/campanha-03nov-state.json")
BRAZIL = ZoneInfo("America/Sao_Paulo")


def check_file(item):
    file_name = item["file"]
    if not file_name.startswith("assets/") or ".." in file_name or Path(file_name).is_absolute():
        raise RuntimeError("Arquivo não autorizado: " + file_name)
    path = Path(file_name)
    if not path.is_file():
        raise RuntimeError("Arquivo não encontrado: " + file_name)
    with path.open("rb") as handle:
        header = handle.read(32)
    if item["kind"] == "post":
        if not file_name.endswith(".png") or header[:8] != b"\\x89PNG\\r\\n\\x1a\\n":
            raise RuntimeError("Post estático não é PNG: " + file_name)
        width, height = struct.unpack(">II", header[16:24])
        if min(width, height) < 600:
            raise RuntimeError("Imagem com resolução baixa: " + str((width,height)))
    else:
        if not file_name.endswith(".mp4") or header[4:8] != b"ftyp":
            raise RuntimeError("Arquivo não é MP4 válido: " + file_name)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=width,height,avg_frame_rate:format=duration",
             "-select_streams", "v:0", "-of", "json", str(path)],
            capture_output=True, text=True, check=True,
        )
        doc = json.loads(probe.stdout)
        stream = (doc.get("streams") or [{}])[0]
        width, height = int(stream.get("width", 0)), int(stream.get("height", 0))
        duration = float((doc.get("format") or {}).get("duration") or 0)
        fps = str(stream.get("avg_frame_rate") or "0/1").split("/")
        fr = float(fps[0]) / float(fps[1]) if len(fps) == 2 and float(fps[1]) else 0
        if min(width, height) < 360 or not (3 <= duration <= 180) or not (23 <= fr <= 60):
            raise RuntimeError("Vídeo fora do formato seguro: " + file_name +
                               " (resolução " + str((width,height)) +
                               ", duração " + str(round(duration,2)) + ", fps " + str(round(fr,2)) + ")")
        if item["kind"] == "story" and duration > 60:
            raise RuntimeError("Story acima de 60s: " + file_name)
    url = "https://raw.githubusercontent.com/" + REPO + "/main/" + file_name
    request = urllib.request.Request(url, headers={
        "User-Agent": "kit-controle-facil-campanha/1.0", "Range": "bytes=0-31",
    })
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            remote = response.read(32)
            if response.status not in (200, 206):
                raise RuntimeError("HTTP de mídia inesperado: " + str(response.status))
            if header[:8] != remote[:8]:
                raise RuntimeError("O link público não corresponde ao arquivo do GitHub: " + file_name)
    except urllib.error.URLError as exc:
        raise RuntimeError("Mídia pública não acessível: " + file_name) from exc
    return url


def scheduled_time(config, service, index):
    day = date.fromisoformat(config["date"])
    hh, mm = map(int, config["start_times"][service].split(":"))
    local = datetime.combine(day, time(hh, mm), tzinfo=BRAZIL) + timedelta(
        minutes=config["interval_minutes"] * index
    )
    return local.astimezone(timezone.utc)


def create_post(token, item, service, channel_id, due_at, media_url):
    kind = item["kind"] if service == "instagram" else "reel"
    media = "image" if kind == "post" else "video"
    metadata = (
        "metadata: { instagram: { type: " + kind + ", shouldShareToFeed: " +
        ("false" if kind == "story" else "true") + " } }"
    ) if service == "instagram" else ""
    due = due_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    document = (
        "mutation { createPost(input: { text: " + gql_string(item["caption"]) +
        " channelId: " + gql_string(channel_id) +
        " schedulingType: automatic mode: customScheduled dueAt: " + gql_string(due) +
        " " + metadata + " assets: [{ " + media + ": { url: " +
        gql_string(media_url) + " } }] }) { __typename " +
        "... on PostActionSuccess { post { id dueAt status } } " +
        "... on MutationError { message } } }"
    )
    result = query_graphql(document, token).get("createPost") or {}
    post = result.get("post") or {}
    if result.get("__typename") != "PostActionSuccess" or not post.get("id"):
        raise RuntimeError(
            "Buffer recusou " + item["slug"] + " / " + service +
            ": " + str(result.get("message") or result)
        )
    if str(post.get("status") or "").lower() not in ("scheduled", "sending"):
        raise RuntimeError("Resposta inesperada do Buffer para " + item["slug"] +
                           ": " + str(post))
    return post


def persist(state):
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    token = os.environ.get("BUFFER_API_KEY","").strip()
    if not token:
        raise RuntimeError("Secret BUFFER_API_KEY ausente.")
    dry_run = os.environ.get("DRY_RUN","true").lower() != "false"
    config = json.loads(DATA.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))
    record = state.setdefault("records", {})
    if config["interval_minutes"] != 10:
        raise RuntimeError("Intervalo da campanha foi alterado; bloqueado.")
    channels = locate_channels(token)
    history = {service: fetch_posts(token, info["org_id"], info["id"])
               for service, info in channels.items()}
    pending = {service: sum(1 for p in posts if str(p.get("status") or "").lower()
                             in ("scheduled","sending")) for service, posts in history.items()}
    count = {service:0 for service in EXPECTED_CHANNELS}
    todo = []
    seen_slugs=set()
    now = datetime.now(timezone.utc)

    # Pré-validação completa de arquivos, links, horários e espaço na fila.
    for item in config["items"]:
        slug=item["slug"]
        if slug in seen_slugs or not item.get("marker") or not item.get("file"):
            raise RuntimeError("Slug repetido / marcador ausente: "+slug)
        seen_slugs.add(slug)
        if item["kind"] not in ("reel","story","post"):
            raise RuntimeError("Tipo inválido: "+slug)
        if not set(item["channels"]).issubset(EXPECTED_CHANNELS):
            raise RuntimeError("Canal inválido: "+slug)
        if item["kind"] != "story" and item["marker"] not in item["caption"]:
            raise RuntimeError("Legenda sem marcador: "+slug)
        media_url=check_file(item)
        for service in item["channels"]:
            key=slug+":"+service
            when=scheduled_time(config,service,count[service])
            count[service]+=1
            if key in record:
                print("JÁ REGISTRADO:",key,"Buffer id:",record[key].get("id"))
                continue
            matches=[p for p in history[service] if is_duplicate(p,item)]
            if matches:
                if len(matches)>1:
                    raise RuntimeError("Possíveis publicações duplicadas de "+key)
                record[key]={"id":matches[0]["id"],"origin":"already_exists"}
                print("JÁ EXISTE NO BUFFER:",key,"|",matches[0]["id"])
                continue
            if when <= now + timedelta(minutes=15):
                raise RuntimeError("Horário já passou ou está muito próximo: "+key)
            todo.append((item,service,when,media_url,key))

    for service in channels:
        added=sum(1 for _,svc,_,_,_ in todo if svc==service)
        if pending[service]+added>10:
            raise RuntimeError(
                "Limite Free de 10 na fila "+service+": "+str(pending[service])+
                " existentes + "+str(added)+" novos. Nada criado."
            )
    if not dry_run:
        persist(state)
    print("SIMULAÇÃO" if dry_run else "ENVIO REAL","|",len(todo),"publicações novas.")
    for item,service,when,url,key in todo:
        display=when.astimezone(BRAZIL).strftime("%d/%m/%Y %H:%M")
        if dry_run:
            print("PREVISTO:",key,"|",display,"Brasília")
            continue
        post=create_post(token,item,service,channels[service]["id"],when,url)
        record[key]={"id":post["id"],"dueAt":post.get("dueAt"),"origin":"campaign"}
        persist(state)
        history[service].append({"id":post["id"],"text":item["caption"],
                                 "assets":[{"source":url}], "status":"scheduled"})
        print("AGENDADO:",key,"|",display,"Brasília | Buffer ID:",post["id"])
    print("CONCLUÍDO:","modo teste" if dry_run else "agendamento feito sem sobrescrever posts antigos.")


if __name__=="__main__":
    try:
        main()
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        print("CAMPANHA BLOQUEADA:",str(exc),file=sys.stderr)
        sys.exit(1)
