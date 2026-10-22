# Development-only public-reference retrieval; never a product/CI service.
# Build existing worker and checks-web images from their locked Dockerfiles first.
FROM motion-xray-worker:latest
COPY --from=motion-xray-checks-web:latest /usr/local/bin/node /usr/local/bin/node
RUN pip install --no-cache-dir --no-deps yt-dlp==2026.10.21 yt-dlp-ejs==0.8.0
ENTRYPOINT ["python", "-m", "yt_dlp"]
