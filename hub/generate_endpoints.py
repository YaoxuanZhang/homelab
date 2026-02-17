import os
import sys

# Define the apps
APPS = [
    "Traefik",
    "Netdata",
    "Kuma",
    "Whoami",
    "Paperless",
    "Nextcloud",
    "Gatus",
]


def get_domain():
    domain_name = os.environ.get("DOMAIN_NAME")
    if not domain_name:
        if len(sys.argv) > 1:
            domain_name = sys.argv[1]
        else:
            print(
                "Error: DOMAIN_NAME environment variable not set and not provided as argument."
            )
            sys.exit(1)
    return domain_name


def generate_authentik_blueprints(domain_name):
    print(f"Generating Authentik blueprints for domain: {domain_name}")
    output_lines = []
    output_lines.append("version: 1")
    output_lines.append("entries:")

    for name in APPS:
        slug = name.lower().replace(" ", "-")
        display_name = name
        external_host = f"{slug}.{domain_name}"
        provider_name = f"Provider for {display_name}"

        # Provider Entry
        output_lines.append(f"  - model: authentik_providers_proxy.proxyprovider")
        output_lines.append(f"    identifiers:")
        output_lines.append(f'      name: "{provider_name}"')
        output_lines.append(f"    attrs:")
        output_lines.append(f"      internal_host_ssl_validation: true")
        output_lines.append(f"      mode: forward_single")
        output_lines.append(f"      external_host: https://{external_host}")
        output_lines.append(f"      intercept_header_auth: true")
        output_lines.append(
            f"      authorization_flow: !Find [authentik_flows.flow, [slug, default-provider-authorization-implicit-consent]]"
        )
        output_lines.append(
            f"      invalidation_flow: !Find [authentik_flows.flow, [slug, default-provider-invalidation-flow]]"
        )
        output_lines.append(f"")

        # Application Entry
        output_lines.append(f"  - model: authentik_core.application")
        output_lines.append(f"    identifiers:")
        output_lines.append(f"      slug: {slug}")
        output_lines.append(f"    attrs:")
        output_lines.append(f"      name: {display_name}")
        output_lines.append(f"      policy_engine_mode: any")
        output_lines.append(
            f'      provider: !Find [authentik_providers_proxy.proxyprovider, [name, "{provider_name}"]]'
        )
        output_lines.append(f"")

    # Outpost Entry
    output_lines.append(f"  - model: authentik_outposts.outpost")
    output_lines.append(f"    identifiers:")
    output_lines.append(f'      name: "authentik Embedded Outpost"')
    output_lines.append(f"    attrs:")
    output_lines.append(f"      providers:")
    for name in APPS:
        provider_name = f"Provider for {name}"
        output_lines.append(
            f'        - !Find [authentik_providers_proxy.proxyprovider, [name, "{provider_name}"]]'
        )

    output_path = os.path.join(
        os.path.dirname(__file__), "authentik/blueprints/hub-apps.yaml"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(output_lines))
    print(f"Successfully generated {output_path}")


def generate_gatus_config(domain_name):
    print(f"Generating Gatus config for domain: {domain_name}")
    output_lines = []

    # Header
    output_lines.append("# Gatus Configuration - Generated")
    output_lines.append("storage:")
    output_lines.append("  type: sqlite")
    output_lines.append("  path: /data/data.db")
    output_lines.append("")

    output_lines.append("ui:")
    output_lines.append('  title: "Service Status"')
    output_lines.append('  header: "Uptime Monitor"')
    output_lines.append("")

    output_lines.append("endpoints:")

    # Always include internal health check
    output_lines.append("  - name: gatus-internal")
    output_lines.append("    group: core")
    output_lines.append('    url: "http://localhost:8080/health"')
    output_lines.append("    interval: 1m")
    output_lines.append("    conditions:")
    output_lines.append('      - "[STATUS] == 200"')
    output_lines.append("")

    for name in APPS:
        slug = name.lower().replace(" ", "-")
        # Gatus itself might be redundant to check via external URL if inside same network, but usage via external simplified.
        # Ensure we use https
        url = f"https://{slug}.{domain_name}"

        output_lines.append(f"  - name: {name}")
        output_lines.append(f"    group: services")
        output_lines.append(f'    url: "{url}"')
        output_lines.append(f"    interval: 1m")
        output_lines.append(f"    conditions:")
        output_lines.append(f'      - "[STATUS] == 200"')
        output_lines.append("")

    output_path = os.path.join(os.path.dirname(__file__), "gatus/config/config.yaml")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(output_lines))
    print(f"Successfully generated {output_path}")


def main():
    domain_name = get_domain()
    generate_authentik_blueprints(domain_name)
    generate_gatus_config(domain_name)


if __name__ == "__main__":
    main()
