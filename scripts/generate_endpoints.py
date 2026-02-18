import os
import sys
import yaml
from dotenv import load_dotenv

load_dotenv()


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
    return domain_name.strip()


def find_docker_compose_files(root_dir):
    compose_files = []
    for root, dirs, files in os.walk(root_dir):
        if "docker-compose.yml" in files:
            compose_files.append(os.path.join(root, "docker-compose.yml"))
    return compose_files


def parse_compose_file(file_path):
    endpoints = []
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

    if not data or "services" not in data:
        return []

    for service_name, service_config in data["services"].items():
        labels = service_config.get("labels", [])
        if not labels:
            continue

        # Convert list of 'key=value' strings to dict for easier checking
        label_dict = {}
        if isinstance(labels, list):
            for label in labels:
                if "=" in label:
                    key, value = label.split("=", 1)
                    label_dict[key] = value
        elif isinstance(labels, dict):
            label_dict = labels

        if label_dict.get("traefik.enable") == "true":
            # Find the Host rule
            # expected format: traefik.http.routers.<name>.rule=Host(`sub.domain.com`)
            host_rule = None
            for key, value in label_dict.items():
                if "traefik.http.routers" in key and ".rule" in key:
                    if "Host(" in value:
                        host_rule = value
                        break

            if host_rule:
                # Extract subdomain. Assuming Host(`...`) format.
                # Simplistic extraction: look for existing value inside ` `
                # This might need to be more robust if there are multiple hosts or different quoting
                try:
                    # value is like: Host(`whoami.${DOMAIN_NAME}`)
                    start = host_rule.find("`") + 1
                    end = host_rule.find("`", start)
                    if start > 0 and end > start:
                        full_host = host_rule[start:end]
                        # We want the name to be the capital subdomain.
                        # If full_host is "whoami.${DOMAIN_NAME}", subdomain is "whoami"
                        if ".${DOMAIN_NAME}" in full_host:
                            subdomain = full_host.replace(".${DOMAIN_NAME}", "")
                            # name = subdomain.capitalize() # Capitalize first letter
                            # The user requested "capital subdomain", e.g. "whoami" -> "Whoami"
                            # There might be cases like "uptime-kuma" -> "Uptime-kuma" or "Uptime Kuma"
                            # Let's just capitalize the first letter for now.
                            name = subdomain.capitalize()
                            url = f"https://{full_host}"
                            endpoints.append(
                                {"name": name, "url": url, "group": "services"}
                            )
                except Exception as e:
                    print(f"Error parsing host rule '{host_rule}' in {file_path}: {e}")

    return endpoints


def generate_gatus_config(domain_name, endpoints):
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

    # Deduplicate endpoints by name to avoid issues if same service in multiple files (unlikely but possible)
    seen = set()

    # Sort endpoints by name for consistent output
    endpoints.sort(key=lambda x: x["name"])

    for endpoint in endpoints:
        name = endpoint["name"]
        if name in seen:
            continue
        seen.add(name)

        url = endpoint["url"]
        group = endpoint.get("group", "services")

        output_lines.append(f"  - name: {name}")
        output_lines.append(f"    group: {group}")
        output_lines.append(f'    url: "{url}"')
        output_lines.append(f"    interval: 1m")
        output_lines.append(f"    conditions:")
        output_lines.append(f'      - "[STATUS] == 200"')
        output_lines.append("")

    # Go up one level from scripts/ to get to repo root
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(repo_root, "hub/gatus/config/config.yaml")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(output_lines))
    print(f"Successfully generated {output_path}")


def main():
    domain_name = get_domain()
    # Go up one level from scripts/ to get to repo root
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print(f"Scanning for docker-compose.yml files in {root_dir}...")
    compose_files = find_docker_compose_files(root_dir)

    all_endpoints = []
    for cf in compose_files:
        endpoints = parse_compose_file(cf)
        all_endpoints.extend(endpoints)

    print(f"Found {len(all_endpoints)} services with Traefik enabled.")
    generate_gatus_config(domain_name, all_endpoints)


if __name__ == "__main__":
    main()
