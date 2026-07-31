#!/usr/bin/env python
"""
Compare the deepface and onnx face backends on real images.

Usage:
    python scripts/benchmark_face_backends.py <image-dir> [--runs 3]

<image-dir> should contain subdirectories, one per person, each holding two or
more photos of that person:

    faces/
      druell/   img1.jpg  img2.jpg
      korin/    img1.jpg  img2.jpg

Reported per backend:

    latency        median and p95 milliseconds per embedding
    same-person    mean cosine similarity between photos of one person
    diff-person    mean cosine similarity between photos of different people
    separation     same-person minus diff-person

Separation is the number that matters. Latency only tells you which is
faster; separation tells you which actually distinguishes people, and a
backend that is quick but cannot separate is useless. It also indicates
whether FACE_MATCHING_THRESHOLD (currently 0.65) suits each backend — a
threshold tuned for Facenet512 will not necessarily suit ArcFace.

The two backends are NOT compared against each other directly: Facenet512 and
ArcFace embed into different vector spaces, so a cosine similarity across them
is noise. Each is scored on its own separation, and those scores compared.
"""
import argparse
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('SECRET_KEY', 'benchmark-only')

import django  # noqa: E402
django.setup()

from students.backends import DEEPFACE, ONNX, extract_embedding  # noqa: E402
from students.face import cosine_similarity  # noqa: E402

IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}


def load_people(root):
	"""{person_name: [image paths]} from one directory per person."""
	people = {}
	for person_dir in sorted(p for p in Path(root).iterdir() if p.is_dir()):
		images = sorted(
			p for p in person_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES
		)
		if images:
			people[person_dir.name] = images
	return people


def embed_all(people, backend, runs):
	"""Embed every image; return ({person: [vectors]}, [latencies_ms], [failures])."""
	vectors, latencies, failures = {}, [], []

	for person, images in people.items():
		vectors[person] = []
		for image_path in images:
			try:
				# Time repeated runs; keep the last vector.
				for _ in range(runs):
					with open(image_path, 'rb') as handle:
						started = time.perf_counter()
						result = extract_embedding(handle, backend=backend)
						latencies.append((time.perf_counter() - started) * 1000)
				vectors[person].append(result['embedding'])
			except Exception as exc:
				failures.append(f'{image_path.name}: {type(exc).__name__}: {exc}')

	return vectors, latencies, failures


def similarity_stats(vectors):
	"""Mean cosine similarity within a person, and across different people."""
	same, different = [], []
	names = list(vectors)

	for i, person in enumerate(names):
		group = vectors[person]
		for a in range(len(group)):
			for b in range(a + 1, len(group)):
				same.append(cosine_similarity(group[a], group[b]))
			for other in names[i + 1:]:
				for vector in vectors[other]:
					different.append(cosine_similarity(group[a], vector))

	return (
		statistics.mean(same) if same else float('nan'),
		statistics.mean(different) if different else float('nan'),
	)


def percentile(values, fraction):
	if not values:
		return float('nan')
	ordered = sorted(values)
	return ordered[min(int(len(ordered) * fraction), len(ordered) - 1)]


def run_backend(backend, people, runs):
	print(f'\n=== {backend} ===')
	try:
		vectors, latencies, failures = embed_all(people, backend, runs)
	except RuntimeError as exc:
		# Missing onnxruntime or missing model files — expected until set up.
		print(f'  unavailable: {exc}')
		return None

	embedded = sum(len(v) for v in vectors.values())
	if not embedded:
		print('  no images could be embedded')
		for failure in failures[:5]:
			print(f'    {failure}')
		return None

	same, different = similarity_stats(vectors)
	report = {
		'backend': backend,
		'images': embedded,
		'median_ms': statistics.median(latencies),
		'p95_ms': percentile(latencies, 0.95),
		'same': same,
		'different': different,
		'separation': same - different,
	}

	print(f'  images embedded : {embedded}')
	print(f'  latency median  : {report["median_ms"]:.0f} ms')
	print(f'  latency p95     : {report["p95_ms"]:.0f} ms')
	print(f'  same-person sim : {same:.4f}')
	print(f'  diff-person sim : {different:.4f}')
	print(f'  separation      : {report["separation"]:.4f}')
	if failures:
		print(f'  failures        : {len(failures)}')
		for failure in failures[:5]:
			print(f'    {failure}')
	return report


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument('image_dir', help='directory with one subdirectory per person')
	parser.add_argument('--runs', type=int, default=3, help='timed runs per image')
	args = parser.parse_args()

	people = load_people(args.image_dir)
	if len(people) < 2:
		print('Need at least two people (two subdirectories) to measure separation.')
		return 1

	total = sum(len(v) for v in people.values())
	print(f'{len(people)} people, {total} images, {args.runs} timed run(s) each')

	reports = [r for r in (run_backend(b, people, args.runs) for b in (DEEPFACE, ONNX)) if r]

	if len(reports) == 2:
		a, b = reports
		print('\n=== verdict ===')
		faster = a if a['median_ms'] < b['median_ms'] else b
		sharper = a if a['separation'] > b['separation'] else b
		print(f'  faster            : {faster["backend"]}')
		print(f'  better separation : {sharper["backend"]}')
		print('\nPrefer separation. Latency matters only among backends that '
		      'reliably tell people apart.')
	elif len(reports) == 1:
		print('\nOnly one backend ran — see requirements-onnx.txt to enable the other.')

	return 0


if __name__ == '__main__':
	raise SystemExit(main())
