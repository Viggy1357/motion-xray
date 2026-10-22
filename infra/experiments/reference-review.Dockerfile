# Local static review only; not the authenticated application artifact endpoint.
FROM motion-xray-api:latest
RUN pip install --no-cache-dir --no-deps RangeHTTPServer==1.4.0
WORKDIR /review
ENTRYPOINT ["python", "-m", "RangeHTTPServer"]
CMD ["8865"]
