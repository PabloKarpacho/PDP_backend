FROM quay.io/keycloak/keycloak:23.0.7

USER root

COPY certs/keycloak /opt/keycloak/certs

RUN chown -R keycloak:keycloak /opt/keycloak/certs && \
    chmod 755 /opt/keycloak/certs && \
    if [ -f /opt/keycloak/certs/cert.pem ]; then chmod 644 /opt/keycloak/certs/cert.pem; fi && \
    if [ -f /opt/keycloak/certs/key.pem ]; then chmod 600 /opt/keycloak/certs/key.pem; fi

USER keycloak

ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
