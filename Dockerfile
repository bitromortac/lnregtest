FROM python:3.10-slim as builder

#################################################################
# INSTALL BITCOIN
#################################################################
ARG BITCOIN_VERSION=22.0
ARG BITCOIN_URL=https://bitcoincore.org/bin/bitcoin-core-22.0
ARG BITCOIN_FILE=bitcoin-${BITCOIN_VERSION}-x86_64-linux-gnu.tar.gz
ARG BITCOIN_SHASUMS=SHA256SUMS
ARG BITCOIN_SHASUMS_ASC=SHA256SUMS.asc

# keys to fetch from ubuntu keyserver
ARG KEYS1='71A3B16735405025D447E8F274810B012346C9A6 01EA5486DE18A882D4C2684590C8019E36C2E964 0CCBAAFD76A2ECE2CCD3141DE2FFD5B1D88CA97D 152812300785C96444D3334D17565732E08E5E41 0AD83877C1F0CD1EE9BD660AD7CC770B81FD22A8 590B7292695AFFA5B672CBB2E13FC145CD3F4304 28F5900B1BB5D1A4B6B6D1A9ED357015286A333D CFB16E21C950F67FA95E558F2EEB9F5CC09526C1 6E01EEC9656903B0542B8F1003DB6322267C373B D1DBF2C4B96F2DEBF4C16654410108112E7EA81F 9D3CC86A72F8494342EA5FD10A41BDC3F4FAFF1C 74E2DEF5D77260B98BC19438099BAD163C70FBFA'
# keys to fetch from keys.openpgp.org
ARG KEYS2='637DB1E23370F84AFF88CCE03152347D07DA627C 82921A4B88FD454B7EB8CE3C796C4109063D4EAF'
# Bitcoin keys (all)
ARG KEYS="${KEYS1} ${KEYS2}"

RUN set -ex && \
    apt-get update && \
    apt-get install -qq --no-install-recommends ca-certificates dirmngr gosu gpg gpg-agent wget git && \
    rm -rf /var/lib/apt/lists/*

# Fetch and install bitcoin binaries
RUN set -ex && \
    mkdir /out && \
    cd /tmp && \
    gpg --batch --keyserver keyserver.ubuntu.com  --recv-keys $KEYS1 && \
    gpg --batch --keyserver keys.openpgp.org  --recv-keys $KEYS2 && \
    gpg --list-keys | tail -n +3 | tee /tmp/keys.txt && \
    gpg --list-keys $KEYS | diff - /tmp/keys.txt && \
    wget -qO "$BITCOIN_SHASUMS" "$BITCOIN_URL/$BITCOIN_SHASUMS" && \
    wget -qO "$BITCOIN_SHASUMS_ASC" "$BITCOIN_URL/$BITCOIN_SHASUMS_ASC" && \
    wget -qO "$BITCOIN_FILE" "$BITCOIN_URL/$BITCOIN_FILE" && \
    gpg --batch --verify "$BITCOIN_SHASUMS_ASC" "$BITCOIN_SHASUMS" && \
    sha256sum --ignore-missing --check "$BITCOIN_SHASUMS" && \
    tar -xzvf "$BITCOIN_FILE" -C /out --strip-components=1 --exclude=*-qt --exclude=share --exclude=README.md && \
    rm -rf /tmp/*


#################################################################
# INSTALL LND
#################################################################

ARG LND_VERSION=v0.14.3-beta
ARG LND_URL=https://github.com/lightningnetwork/lnd/releases/download/${LND_VERSION}
ARG LND_FILE=lnd-linux-amd64-${LND_VERSION}.tar.gz
ARG LND_SHASUMS=manifest-${LND_VERSION}.txt
ARG LND_SHASUMS_ASC=manifest-roasbeef-${LND_VERSION}.sig 

# keys to fetch from ubuntu keyserver (roasbeef)
ARG LND_KEYS1='E4D85299674B2D31FAA1892E372CBD7633C61696'
# keys to fetch from keys.openpgp.org
ARG LND_KEYS2='E4D85299674B2D31FAA1892E372CBD7633C61696'

# Fetch and install lnd binaries
RUN set -ex && \
    cd /tmp && \
    gpg --batch --keyserver keyserver.ubuntu.com  --recv-keys $LND_KEYS1 && \
    gpg --batch --keyserver keys.openpgp.org  --recv-keys $LND_KEYS2 && \
    wget -qO "$LND_SHASUMS" "$LND_URL/$LND_SHASUMS" && \
    wget -qO "$LND_SHASUMS_ASC" "$LND_URL/$LND_SHASUMS_ASC" && \
    wget -qO "$LND_FILE" "$LND_URL/$LND_FILE" && \
    gpg --batch --verify "$LND_SHASUMS_ASC" "$LND_SHASUMS" && \
    sha256sum --ignore-missing --check "$LND_SHASUMS" && \
    tar -xzvf "$LND_FILE" -C /out/bin --strip-components=1 && \
    rm -rf /tmp/*

#################################################################
# INSTALL ELECTRUM
#################################################################

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY . .

ARG ELECTRUM_REF=4.2.1
ARG ELECTRUMX_REF=265a5a87b8ad01f739049c0b1e80923aab318f58

RUN pip install wheel && ./contrib/install_electrum.sh

#################################################################
# FINAL IMAGE
#################################################################

FROM python:3.10-slim

RUN set -ex && \
    apt-get update && \
    apt-get install -qq --no-install-recommends ca-certificates libsecp256k1-0 python3-pyqt5 gosu && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home user

COPY --from=builder /out /opt
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=user /app /home/user/app

ENV PATH="/opt/venv/bin:/opt/bin:$PATH"

WORKDIR /home/user/app

ENTRYPOINT ["contrib/docker-entrypoint.sh"]
