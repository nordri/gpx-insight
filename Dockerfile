FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

ENV MPLCONFIGDIR=/tmp/matplotlib
ENV XDG_CACHE_HOME=/tmp/.cache

RUN dnf install -y cairo dejavu-sans-fonts \
    && mkdir -p /usr/share/fonts/truetype \
    && ln -s /usr/share/fonts/dejavu-sans-fonts /usr/share/fonts/truetype/dejavu \
    && ln -s /usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf "${LAMBDA_TASK_ROOT}/DejaVuSans.ttf" \
    && ln -s /usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf "${LAMBDA_TASK_ROOT}/DejaVuSans-Bold.ttf" \
    && dnf clean all

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY cli.py ./
COPY service.py ./
COPY handler.py ./
COPY analytics/ ./analytics/
COPY parser/ ./parser/
COPY rendering/ ./rendering/
COPY i18n/ ./i18n/

CMD ["handler.lambda_handler"]
