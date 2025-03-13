import tablib


class CsvExporter:

    def export(self, rows):
        dataset = tablib.Dataset()
        if not rows:
            return dataset
        headers = list(rows[0].keys())
        dataset.headers = headers
        for row in rows:
            dataset.append([row.get(h) for h in headers])
        return dataset
