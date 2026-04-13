import csv
import io


def publications_to_csv(publications):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "title", "type", "year", "venue", "ranking", "doi"])

    for pub in publications:
        writer.writerow([
            pub.id,
            pub.title,
            pub.publication_type,
            pub.year,
            pub.venue_name or "",
            pub.ranking or "",
            pub.doi or "",
        ])

    return output.getvalue()


def publications_to_bibtex(publications):
    items = []
    for pub in publications:
        key = f"{(pub.title or 'pub').split()[0].lower()}{pub.year}{pub.id}"
        lines = [
            f"@article{{{key},",
            f"  title = {{{pub.title}}},",
            f"  year = {{{pub.year}}},",
        ]
        if pub.venue_name:
            lines.append(f"  journal = {{{pub.venue_name}}},")
        if pub.doi:
            lines.append(f"  doi = {{{pub.doi}}},")
        if pub.external_url:
            lines.append(f"  url = {{{pub.external_url}}},")
        lines.append("}")
        items.append("\n".join(lines))

    return "\n\n".join(items) + "\n"
