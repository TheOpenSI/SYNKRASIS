from __future__ import annotations

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from dataclasses import dataclass, field
from typing import Any

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class VisualiserConfig:
    """Configuration for the DAG visualiser.

    Args:
        figsize (tuple[int, int]): Figure width and height in inches.
        node_radius (float | None): Radius of each node circle in data coordinates.
            If None, auto-computed from the layout bounds.
        node_label_fontsize (int): Font size for node labels.
        edge_label_fontsize (int): Font size for edge data flow labels.
        phase_label_fontsize (int): Font size for phase column headers.
        phase_band_alpha (float): Opacity of the phase background bands.
        parallel_group_alpha (float): Opacity of the parallel group background rectangles.
        output_path (str): File path to save the rendered PNG.
        dpi (int): Output resolution.
        x_pad (float): Horizontal padding added around the layout bounds.
        y_pad (float): Vertical padding added around the layout bounds.
    """
    figsize: tuple[int, int] = (32, 18)
    node_radius: float | None = None
    node_label_fontsize: int = 7
    edge_label_fontsize: int = 6
    phase_label_fontsize: int = 10
    phase_band_alpha: float = 0.28
    parallel_group_alpha: float = 0.18
    output_path: str = "dag_output.png"
    dpi: int = 180
    x_pad: float = 0.3
    y_pad: float = 0.3


# ---------------------------------------------------------------------------
# Colour and style constants
# ---------------------------------------------------------------------------

COLOUR_CRITICAL = "#c0392b"
COLOUR_NON_CRITICAL = "#2980b9"
COLOUR_ITERATIVE_BORDER = "#8e44ad"
COLOUR_SEQUENTIAL_BORDER = "#2c3e50"
COLOUR_PARALLEL_BORDER = "#16a085"
COLOUR_PHASE_BANDS = [
    "#eaf4fb", "#eafaf1", "#fef9e7",
    "#fdedec", "#f4ecf7", "#e8f8f5",
]
COLOUR_PARALLEL_GROUP = "#e67e22"
COLOUR_EDGE = "#666666"


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

@dataclass
class _NodeStyle:
    """Resolved visual style for a single node.

    Args:
        fill_colour (str): Node interior colour based on criticality.
        border_colour (str): Node border colour based on execution type.
        border_width (float): Border line width.
        is_iterative (bool): Whether to render a dashed border.
        is_parallel_exec (bool): Whether to render a double border ring.
    """
    fill_colour: str
    border_colour: str
    border_width: float
    is_iterative: bool
    is_parallel_exec: bool


@dataclass
class _LayoutBounds:
    """Computed bounds of the node layout with padding.

    Args:
        x_min (float): Left boundary.
        x_max (float): Right boundary.
        y_min (float): Bottom boundary.
        y_max (float): Top boundary.
        node_radius (float): Auto or manually configured node radius.
    """
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    node_radius: float


# ---------------------------------------------------------------------------
# DAG Visualiser
# ---------------------------------------------------------------------------

class DAGVisualiser:
    """Renders a fault-tolerant DAG specification as a matplotlib figure.

    Takes the output from the Fault Tolerance Specification agent and produces
    a structured, phase-aligned visual graph encoding criticality, execution
    type, parallel groups, and fault tolerance summaries per node.

    Args:
        fault_tolerance_output (dict[str, Any]): The full output from the
            Fault Tolerance Specification agent.
        config (VisualiserConfig): Visual configuration options.
    """

    def __init__(
        self,
        fault_tolerance_output: dict[str, Any],
        config: VisualiserConfig | None = None,
    ) -> None:
        self._data = fault_tolerance_output["fault_tolerance_spec"]
        self._process_name = fault_tolerance_output["process_name"]
        self._config = config or VisualiserConfig()
        self._graph: nx.DiGraph = nx.DiGraph()
        self._nodes: list[dict[str, Any]] = self._data["nodes"]
        self._phases: list[dict[str, Any]] = self._data["phases"]
        self._parallel_groups: dict[str, list[str]] = self._data["parallel_groups"]
        self._node_map: dict[str, dict[str, Any]] = {
            n["id"]: n for n in self._nodes
        }
        self._pos: dict[str, tuple[float, float]] = {}
        self._bounds: _LayoutBounds | None = None


    # -----------------------------------------------------------------------
    # Public interface
    # -----------------------------------------------------------------------

    def render(self) -> None:
        """Build the graph, compute layout, and render the figure to disk.

        Returns:
            None
        """
        self._build_graph()
        self._compute_layout()
        self._compute_bounds()

        fig, ax = plt.subplots(figsize=self._config.figsize)
        ax.axis("off")

        # Explicit axis limits prevent matplotlib auto-scaling distortion
        ax.set_xlim(self._bounds.x_min, self._bounds.x_max)
        ax.set_ylim(self._bounds.y_min, self._bounds.y_max)

        self._draw_phase_bands(ax)
        self._draw_parallel_group_boxes(ax)
        self._draw_edges(ax)
        self._draw_nodes(ax)
        self._draw_node_labels(ax)
        self._draw_phase_headers(ax)
        self._draw_legend(ax)
        self._draw_title(ax)

        plt.tight_layout()
        plt.savefig(
            self._config.output_path,
            dpi=self._config.dpi,
            bbox_inches="tight",
            facecolor="white",
        )
        plt.close(fig)
        print(f"DAG visualisation saved to: {self._config.output_path}")


    # -----------------------------------------------------------------------
    # Graph construction
    # -----------------------------------------------------------------------

    def _build_graph(self) -> None:
        """Construct the NetworkX DiGraph from the fault tolerance node list.

        Returns:
            None
        """
        for node in self._nodes:
            phase_index = self._get_phase_index(node["phase"])
            self._graph.add_node(node["id"], subset=phase_index)

        for node in self._nodes:
            for dependency_id in node["depends_on"]:
                self._graph.add_edge(dependency_id, node["id"])


    def _get_phase_index(self, phase_id: str) -> int:
        """Return the zero-based index of a phase in the phases list.

        Args:
            phase_id (str): The phase identifier to look up.

        Returns:
            int: Zero-based index of the phase.
        """
        for i, phase in enumerate(self._phases):
            if phase["phase_id"] == phase_id:
                return i
        return 0


    # -----------------------------------------------------------------------
    # Layout and bounds
    # -----------------------------------------------------------------------

    def _compute_layout(self) -> None:
        """Compute node positions using NetworkX multipartite layout, then
        re-order nodes within each column by topological sort order.

        Multipartite layout places nodes in phase columns correctly but does
        not respect dependency order within a column. The post-processing step
        re-assigns y positions so that nodes earlier in the dependency chain
        appear at the top of their column.

        Returns:
            None
        """
        self._pos = nx.multipartite_layout(
            self._graph,
            subset_key="subset",
            align="vertical",
            scale=2.0,
        )
        self._sort_columns_by_topology()


    def _sort_columns_by_topology(self) -> None:
        """Re-assign y positions within each phase column by topological order.

        After multipartite_layout, nodes in the same column can be in arbitrary
        vertical order. This method groups nodes by their x coordinate (column),
        sorts each group by the node's index in the full topological sort, and
        redistributes the original y values in that sorted order so that
        upstream tasks appear at the top of the column.

        Returns:
            None
        """
        topo_order = {
            node_id: idx
            for idx, node_id in enumerate(nx.topological_sort(self._graph))
        }

        # Group nodes by column (same x coordinate = same phase)
        columns: dict[str, list[str]] = {}
        for node_id, (x, _) in self._pos.items():
            key = f"{x:.4f}"
            columns.setdefault(key, []).append(node_id)

        for node_ids in columns.values():
            if len(node_ids) < 2:
                continue

            # Collect the existing y values for this column, sorted descending
            # (top of column = lowest topo index = smallest topo_order value)
            existing_ys = sorted(
                [self._pos[nid][1] for nid in node_ids],
                reverse=True,
            )

            # Sort node_ids by topological order (earliest dependency first)
            sorted_nodes = sorted(node_ids, key=lambda nid: topo_order.get(nid, 0))

            # Re-assign: top y value goes to the first node in topo order
            for node_id, y in zip(sorted_nodes, existing_ys):
                x = self._pos[node_id][0]
                self._pos[node_id] = (x, y)


    def _compute_bounds(self) -> None:
        """Compute padded layout bounds and auto node radius from position data.

        Node radius is derived from the minimum inter-node spacing within any
        column so that nodes never overlap regardless of how many tasks share
        a phase.

        Returns:
            None
        """
        xs = [p[0] for p in self._pos.values()]
        ys = [p[1] for p in self._pos.values()]

        y_range = max(ys) - min(ys) if max(ys) != min(ys) else 1.0

        if self._config.node_radius is not None:
            radius = self._config.node_radius
        else:
            radius = self._compute_auto_radius()

        pad_x = self._config.x_pad + radius
        pad_y = self._config.y_pad + radius

        # Reserve just enough headroom for a single line of phase header text
        header_space = y_range * 0.09

        self._bounds = _LayoutBounds(
            x_min=min(xs) - pad_x,
            x_max=max(xs) + pad_x,
            y_min=min(ys) - pad_y,
            y_max=max(ys) + pad_y + header_space,
            node_radius=radius,
        )


    def _compute_auto_radius(self) -> float:
        """Compute a node radius that fits within the tightest column spacing.

        Groups nodes by their x coordinate (phase column) and finds the minimum
        vertical gap between nodes in any column. The radius is set to 35% of
        that gap, clamped to a sensible range.

        Returns:
            float: The computed node radius in data coordinates.
        """
        # Group y positions by rounded x coordinate (same column = same phase)
        columns: dict[str, list[float]] = {}
        for node_id, (x, y) in self._pos.items():
            key = f"{x:.3f}"
            columns.setdefault(key, []).append(y)

        min_gap = float("inf")
        for y_vals in columns.values():
            if len(y_vals) < 2:
                continue
            sorted_ys = sorted(y_vals)
            for i in range(len(sorted_ys) - 1):
                gap = sorted_ys[i + 1] - sorted_ys[i]
                min_gap = min(min_gap, gap)

        if min_gap == float("inf"):
            min_gap = 0.6

        radius = min_gap * 0.35
        return max(0.07, min(radius, 0.22))


    # -----------------------------------------------------------------------
    # Drawing — background layers
    # -----------------------------------------------------------------------

    def _draw_phase_bands(self, ax: plt.Axes) -> None:
        """Draw a subtle background rectangle behind each phase column.

        Args:
            ax (plt.Axes): The matplotlib axes to draw on.

        Returns:
            None
        """
        phase_x_groups = self._group_positions_by_phase()
        r = self._bounds.node_radius

        for i, phase in enumerate(self._phases):
            phase_id = phase["phase_id"]
            x_coords = phase_x_groups.get(phase_id, [])
            if not x_coords:
                continue

            colour = COLOUR_PHASE_BANDS[i % len(COLOUR_PHASE_BANDS)]

            # Ensure minimum width for single-node columns
            col_width = max(x_coords) - min(x_coords)
            margin = r + 0.1
            x_left = min(x_coords) - margin
            x_right = max(x_coords) + margin
            if col_width == 0:
                x_left -= margin
                x_right += margin

            rect = mpatches.FancyBboxPatch(
                (x_left, self._bounds.y_min + 0.05),
                x_right - x_left,
                self._bounds.y_max - self._bounds.y_min - 0.1,
                boxstyle="round,pad=0.01",
                linewidth=0.6,
                edgecolor="#cccccc",
                facecolor=colour,
                alpha=self._config.phase_band_alpha,
                zorder=0,
            )
            ax.add_patch(rect)


    def _draw_parallel_group_boxes(self, ax: plt.Axes) -> None:
        """Draw a shaded rectangle behind each parallel group of nodes.

        Args:
            ax (plt.Axes): The matplotlib axes to draw on.

        Returns:
            None
        """
        for group_label, task_ids in self._parallel_groups.items():
            positions = [self._pos[tid] for tid in task_ids if tid in self._pos]
            if not positions:
                continue

            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            r = self._bounds.node_radius
            pad = r + 0.05

            box_x = min(xs) - pad
            box_y = min(ys) - pad
            box_w = (max(xs) - min(xs)) + pad * 2
            box_h = (max(ys) - min(ys)) + pad * 2

            rect = mpatches.FancyBboxPatch(
                (box_x, box_y),
                box_w,
                box_h,
                boxstyle="round,pad=0.01",
                linewidth=1.4,
                edgecolor=COLOUR_PARALLEL_GROUP,
                facecolor=COLOUR_PARALLEL_GROUP,
                alpha=self._config.parallel_group_alpha,
                zorder=1,
            )
            ax.add_patch(rect)

            ax.text(
                (min(xs) + max(xs)) / 2,
                min(ys) - pad - 0.04,
                group_label,
                fontsize=7,
                ha="center",
                va="top",
                color=COLOUR_PARALLEL_GROUP,
                fontweight="bold",
                zorder=5,
            )


    # -----------------------------------------------------------------------
    # Drawing — edges
    # -----------------------------------------------------------------------

    def _draw_edges(self, ax: plt.Axes) -> None:
        """Draw directed edges with arrowheads and truncated data flow labels.

        Args:
            ax (plt.Axes): The matplotlib axes to draw on.

        Returns:
            None
        """
        for source_id, target_id in self._graph.edges():
            x_start, y_start = self._pos[source_id]
            x_end, y_end = self._pos[target_id]
            r = self._bounds.node_radius

            dx = x_end - x_start
            dy = y_end - y_start
            length = np.sqrt(dx ** 2 + dy ** 2)
            if length == 0:
                continue

            ux, uy = dx / length, dy / length
            x0 = x_start + ux * r
            y0 = y_start + uy * r
            x1 = x_end - ux * r
            y1 = y_end - uy * r

            ax.annotate(
                "",
                xy=(x1, y1),
                xytext=(x0, y0),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=COLOUR_EDGE,
                    lw=1.0,
                    mutation_scale=12,
                ),
                zorder=2,
            )

            label = self._get_edge_label(source_id, target_id)
            if label:
                mid_x = (x0 + x1) / 2
                mid_y = (y0 + y1) / 2
                ax.text(
                    mid_x, mid_y,
                    label,
                    fontsize=self._config.edge_label_fontsize,
                    ha="center",
                    va="center",
                    color="#555555",
                    style="italic",
                    bbox=dict(
                        boxstyle="round,pad=0.15",
                        facecolor="white",
                        edgecolor="none",
                        alpha=0.8,
                    ),
                    zorder=3,
                )


    def _get_edge_label(self, source_id: str, target_id: str) -> str:
        """Extract a short data flow label for an edge from the target's consumes field.

        Args:
            source_id (str): The source task ID.
            target_id (str): The target task ID.

        Returns:
            str: A truncated label describing what flows along this edge, or empty string.
        """
        target_node = self._node_map.get(target_id)
        if not target_node:
            return ""

        consumes = target_node.get("consumes", "")
        if not consumes or consumes.lower().startswith("none"):
            return ""

        relevant = [
            part.strip()
            for part in consumes.split(" and ")
            if source_id in part
        ]

        if not relevant:
            return ""

        label = relevant[0].split(" from ")[0].strip()
        if len(label) > 26:
            label = label[:24] + ".."
        return label


    # -----------------------------------------------------------------------
    # Drawing — nodes
    # -----------------------------------------------------------------------

    def _draw_nodes(self, ax: plt.Axes) -> None:
        """Draw each node as a styled circle encoding criticality and execution type.

        Args:
            ax (plt.Axes): The matplotlib axes to draw on.

        Returns:
            None
        """
        r = self._bounds.node_radius

        for node in self._nodes:
            node_id = node["id"]
            x, y = self._pos[node_id]
            style = self._resolve_node_style(node)

            circle = plt.Circle(
                (x, y),
                r,
                color=style.fill_colour,
                ec=style.border_colour,
                linewidth=style.border_width,
                linestyle="--" if style.is_iterative else "-",
                zorder=4,
                alpha=0.92,
            )
            ax.add_patch(circle)

            if style.is_parallel_exec:
                outer_ring = plt.Circle(
                    (x, y),
                    r + r * 0.2,
                    color="none",
                    ec=style.border_colour,
                    linewidth=1.2,
                    zorder=4,
                )
                ax.add_patch(outer_ring)


    def _resolve_node_style(self, node: dict[str, Any]) -> _NodeStyle:
        """Determine the visual style for a node from its fault tolerance attributes.

        Args:
            node (dict[str, Any]): The node dictionary from the fault tolerance spec.

        Returns:
            _NodeStyle: The resolved style for this node.
        """
        ft = node.get("fault_tolerance", {})
        criticality = ft.get("criticality", "non_critical")
        execution_type = node.get("execution_type", "sequential")

        fill_colour = (
            COLOUR_CRITICAL if criticality == "critical"
            else COLOUR_NON_CRITICAL
        )

        border_colour_map = {
            "iterative": COLOUR_ITERATIVE_BORDER,
            "parallel": COLOUR_PARALLEL_BORDER,
            "sequential": COLOUR_SEQUENTIAL_BORDER,
        }
        border_colour = border_colour_map.get(execution_type, COLOUR_SEQUENTIAL_BORDER)

        return _NodeStyle(
            fill_colour=fill_colour,
            border_colour=border_colour,
            border_width=2.2,
            is_iterative=execution_type == "iterative",
            is_parallel_exec=execution_type == "parallel",
        )


    # -----------------------------------------------------------------------
    # Drawing — labels, headers, legend, title
    # -----------------------------------------------------------------------

    def _draw_node_labels(self, ax: plt.Axes) -> None:
        """Draw task ID, truncated description, and fault tolerance summary per node.

        Args:
            ax (plt.Axes): The matplotlib axes to draw on.

        Returns:
            None
        """
        for node in self._nodes:
            node_id = node["id"]
            x, y = self._pos[node_id]
            ft = node.get("fault_tolerance", {})

            max_attempts = ft.get("retry_policy", {}).get("max_attempts", 1)
            fallback_strategy = ft.get("fallback", {}).get("strategy", "halt")

            words = node.get("description", "").split()
            short_desc = " ".join(words[:4])
            if len(words) > 4:
                short_desc += ".."

            label = f"{node_id}\n{short_desc}\n{max_attempts} att. | {fallback_strategy}"

            ax.text(
                x, y,
                label,
                fontsize=self._config.node_label_fontsize,
                ha="center",
                va="center",
                color="white",
                fontweight="bold",
                zorder=5,
                multialignment="center",
                linespacing=1.3,
            )


    def _draw_phase_headers(self, ax: plt.Axes) -> None:
        """Draw phase headers at a consistent y position across all columns.

        All headers sit at the same height — just above the globally highest
        node — so the line of headers is visually uniform regardless of how
        many nodes each column contains.

        Args:
            ax (plt.Axes): The matplotlib axes to draw on.

        Returns:
            None
        """
        phase_x_groups = self._group_positions_by_phase()
        r = self._bounds.node_radius

        # Single global header line above the tallest node in the entire graph
        global_max_y = max(p[1] for p in self._pos.values())
        header_y = global_max_y + r + 0.08

        for phase in self._phases:
            phase_id = phase["phase_id"]
            x_coords = phase_x_groups.get(phase_id, [])
            if not x_coords:
                continue

            mid_x = sum(x_coords) / len(x_coords)

            ax.text(
                mid_x,
                header_y,
                f"{phase_id} — {phase['phase_name']}",
                fontsize=self._config.phase_label_fontsize,
                ha="center",
                va="bottom",
                fontweight="bold",
                color="#2c3e50",
                zorder=5,
            )


    def _draw_title(self, ax: plt.Axes) -> None:
        """Draw the pipeline title using figure-level coordinates to avoid overlap.

        Args:
            ax (plt.Axes): The matplotlib axes to draw on.

        Returns:
            None
        """
        ax.figure.text(
            0.5, 0.985,
            self._process_name,
            fontsize=14,
            fontweight="bold",
            ha="center",
            va="top",
            color="#1a1a2e",
        )


    def _draw_legend(self, ax: plt.Axes) -> None:
        """Draw a legend explaining node colours, borders, and group shading.

        Args:
            ax (plt.Axes): The matplotlib axes to draw on.

        Returns:
            None
        """
        legend_elements = [
            mpatches.Patch(facecolor=COLOUR_CRITICAL, label="Critical task"),
            mpatches.Patch(facecolor=COLOUR_NON_CRITICAL, label="Non-critical task"),
            mpatches.Patch(
                facecolor="white", edgecolor=COLOUR_SEQUENTIAL_BORDER,
                linewidth=2, label="Sequential",
            ),
            mpatches.Patch(
                facecolor="white", edgecolor=COLOUR_ITERATIVE_BORDER,
                linewidth=2, linestyle="--", label="Iterative",
            ),
            mpatches.Patch(
                facecolor="white", edgecolor=COLOUR_PARALLEL_BORDER,
                linewidth=2, label="Parallel (double border)",
            ),
            mpatches.Patch(
                facecolor=COLOUR_PARALLEL_GROUP, alpha=0.4,
                label="Parallel group",
            ),
        ]

        ax.legend(
            handles=legend_elements,
            loc="lower right",
            fontsize=8,
            framealpha=0.92,
            edgecolor="#cccccc",
            title="Legend",
            title_fontsize=9,
        )


    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _group_positions_by_phase(self) -> dict[str, list[float]]:
        """Collect the x coordinates of all nodes grouped by their phase ID.

        Returns:
            dict[str, list[float]]: Mapping of phase ID to list of node x positions.
        """
        groups: dict[str, list[float]] = {
            phase["phase_id"]: [] for phase in self._phases
        }
        for node_id, (x, _) in self._pos.items():
            phase_id = self._node_map[node_id]["phase"]
            if phase_id in groups:
                groups[phase_id].append(x)
        return groups