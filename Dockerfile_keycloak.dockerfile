FROM quay.io/keycloak/keycloak:23.0.7

USER root

COPY certs /opt/keycloak/certs

RUN chown -R keycloak:keycloak /opt/keycloak/certs && \
    chmod 755 /opt/keycloak/certs && \
    chmod 644 /opt/keycloak/certs/cert.pem && \
    chmod 600 /opt/keycloak/certs/key.pem

USER keycloak

ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
