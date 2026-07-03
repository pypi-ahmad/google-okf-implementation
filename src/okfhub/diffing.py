"""Bundle diff utilities for OKF version comparisons."""

from pathlib import Path

from rapidfuzz import fuzz

from okfhub.models import DiffChange, DiffReport
from okfhub.okf import OKFBundleLoader


class OKFDiffService:
    """Compare two OKF bundles and report semantic changes."""

    def diff(self, old_root: Path, new_root: Path) -> DiffReport:
        """Create diff report between old and new bundle roots."""

        loader = OKFBundleLoader()
        old_docs = {doc.concept_id: doc for doc in loader.load(old_root)}
        new_docs = {doc.concept_id: doc for doc in loader.load(new_root)}

        report = DiffReport()

        old_ids = set(old_docs)
        new_ids = set(new_docs)

        for added_id in sorted(new_ids - old_ids):
            doc = new_docs[added_id]
            report.added.append(
                DiffChange(
                    change_type="added",
                    concept_id=added_id,
                    new_path=doc.relative_path,
                    details=doc.frontmatter.title,
                )
            )

        for removed_id in sorted(old_ids - new_ids):
            doc = old_docs[removed_id]
            report.removed.append(
                DiffChange(
                    change_type="removed",
                    concept_id=removed_id,
                    old_path=doc.relative_path,
                    details=doc.frontmatter.title,
                )
            )

        for common_id in sorted(old_ids & new_ids):
            old_doc = old_docs[common_id]
            new_doc = new_docs[common_id]
            changed = (
                old_doc.frontmatter.model_dump() != new_doc.frontmatter.model_dump()
                or old_doc.body.strip() != new_doc.body.strip()
                or sorted(old_doc.links) != sorted(new_doc.links)
            )
            if changed:
                change = DiffChange(
                    change_type="modified",
                    concept_id=common_id,
                    old_path=old_doc.relative_path,
                    new_path=new_doc.relative_path,
                    details="frontmatter/body/links changed",
                )
                report.modified.append(change)
                if old_doc.frontmatter.type == "metric":
                    report.changed_metrics.append(change)

        # Rename hints: removed vs added with high title similarity and same type.
        consumed_added: set[str] = set()
        for removed in report.removed:
            old_doc = old_docs.get(removed.concept_id)
            if old_doc is None:
                continue

            best_id = None
            best_score = 0
            for added in report.added:
                if added.concept_id in consumed_added:
                    continue
                new_doc = new_docs.get(added.concept_id)
                if new_doc is None:
                    continue
                if old_doc.frontmatter.type != new_doc.frontmatter.type:
                    continue
                score = self._rename_score(old_doc.frontmatter.title, new_doc.frontmatter.title)
                resource_score = self._rename_score(
                    old_doc.frontmatter.resource or "",
                    new_doc.frontmatter.resource or "",
                )
                score = max(score, resource_score)
                if score > best_score:
                    best_score = score
                    best_id = added.concept_id

            if best_id and best_score >= 85:
                new_doc = new_docs[best_id]
                rename_change = DiffChange(
                    change_type="renamed",
                    concept_id=removed.concept_id,
                    old_path=old_doc.relative_path,
                    new_path=new_doc.relative_path,
                    details=f"name/resource similarity={best_score}",
                )
                report.renamed.append(rename_change)
                if old_doc.frontmatter.type == "api":
                    report.renamed_apis.append(rename_change)
                consumed_added.add(best_id)

        return report

    def _rename_score(self, old_value: str, new_value: str) -> int:
        old_clean = old_value.lower().strip()
        new_clean = new_value.lower().strip()
        if not old_clean or not new_clean:
            return 0
        return int(fuzz.ratio(old_clean, new_clean))
