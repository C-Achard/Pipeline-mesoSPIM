import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from monai.transforms import RandSpatialCrop
from schema.utils import gitWrapper, spim_sendEmail
from scripts.generate_cell_plot import generate_plot


@dataclass
class Report:
    """Report to send to user after segmentation."""

    email: str
    user: str
    scan_name: str
    roi_name: str
    results_path: str
    stats_summary: dict
    labels: np.array

    def send_report(self):
        """Send report to user."""
        msg_body, samples = self.stats_report()

        plot_path = generate_plot(
            self.labels, self.roi_name, self.results_path, 0.9
        )

        spim_sendEmail.send_report_email(
            email=self.email,
            filename=self.scan_name,
            attachment_file=plot_path,
            message=msg_body,
        )

        print(msg_body)  # TODO(cyril) : add email methods
        print(f"Number of samples: {len(samples)}, size: {samples[0].shape}\n")

    def write_to_csv(self):
        """Write stats summary to csv."""
        with Path(
            f'{str(self.results_path)}/report_{self.stats_summary["mouse_name"]}_{self.stats_summary["scan_attempt"]}.csv'
        ).open(
            "w",
        ) as f:
            w = csv.writer(f)
            w.writerows(self.stats_summary.items())

    def stats_report(self):
        """Generate human-readable stats report for user."""
        msg_body = (
            f"Report test : cellseg3d\n"
            f"Sending to {self.user} at {self.email}\n"
            f"This is a report for the segmentation of the {self.roi_name} region\n"
            f"Stats summary :\n"
            f"Image size: {self.stats_summary['image_size']}\n"
            f"Cell count: {self.stats_summary['cell_counts']}\n"
            f"Density: {self.stats_summary['density']}\n"
            + ("*" * 30)
            + "\n"
            + f"Using Github commit: {gitWrapper.get_last_commit_hash()} made on {gitWrapper.get_last_commit_date()}\n"
        )

        # csv = self.image_stats.get_dict()

        labels = np.expand_dims(self.labels, axis=0)
        samples = [
            np.squeeze(
                RandSpatialCrop([16, 16, 16], random_size=False)(labels)
            )
            for i in range(5)
        ]

        return msg_body, samples
