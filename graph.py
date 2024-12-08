from dataclasses import dataclass
import argparse

@dataclass
class Graph:
    nodes: set[str]
    agent_node_links: dict[str, dict[str, set[str]]]
    agent_colors: dict[str, str]
    realworld: str | None = None
    clusters: dict[str, set['Graph']] | None = None

    @classmethod
    def from_graphviz(cls, f) -> 'Graph':
        nodes = set()
        agent_node_links = dict()
        agent_colors = dict()
        for line in f.readlines():
            line = line.strip()
            if line.startswith('label="'):
                agent = line[7]
                agent_node_links[agent] = dict()
                continue
            if line.startswith('color="'):
                agent_colors[agent] = line[7:-2]
                continue
            if '->' in line:
                bidirectional = line.endswith('[dir=both];')
                if bidirectional:
                    line, _, _ = line.partition('[')
                else:
                    line = line[:-1]
                lhs, _, rhs = tuple(x.strip() for x in line.partition('->'))
                nodes.add(lhs)
                nodes.add(rhs)
                connections = [(lhs, rhs)]
                if bidirectional:
                    connections.append((rhs, lhs))
                for node_from, node_to in connections:
                    try:
                        agent_node_links[agent][node_from].add(node_to)
                    except KeyError:
                        agent_node_links[agent][node_from] = {node_to,}
                continue
        return cls(nodes=nodes, agent_node_links=agent_node_links, agent_colors=agent_colors)

    def to_graphviz_lines(self):
        yield "digraph G {"
        yield "  edge[arrowsize=0.3];"
        for event, worlds in (self.clusters or dict()).items():
            yield ""
            yield f"  subgraph cluster_{event} {{"
            for world in worlds:
                yield f"    {world};"
            yield "  }"
        for agent, node_links in self.agent_node_links.items():
            yield ""
            yield "  edge["
            yield f'    label="{agent}",'
            yield f'    color="{self.agent_colors[agent]}",'
            yield f'    fontcolor="{self.agent_colors[agent]}",'
            yield "  ];"
            for node_from, nodes_to in node_links.items():
                for node_to in nodes_to:
                    bidirectional = node_from != node_to and (node_from in node_links.get(node_to, set()))
                    if bidirectional:
                        if node_from < node_to:
                            yield f"  {node_from} -> {node_to}[dir=both];"
                    else:
                        yield f"  {node_from} -> {node_to};"
        yield "}"

    def to_graphviz(self) -> str:
        return "".join([line + '\n' for line in self.to_graphviz_lines()])

    def product(self, events: 'Graph', compat: dict) -> 'Graph':
        new_agent_world_links = dict()
        new_worlds = set()
        clusters = dict()

        for agent, old_world_links in self.agent_node_links.items():
            new_world_links = dict()
            new_agent_world_links[agent] = new_world_links

            for old_world_from, old_worlds_to in old_world_links.items():
                for old_world_to in old_worlds_to:
                    for event_from, events_to in events.agent_node_links[agent].items():

                        # check from-event precondition
                        if event_from != 'true' and event_from not in compat.get(old_world_from, set()):
                            continue

                        for event_to in events_to:

                            # check to-event precondition
                            if event_to != 'true' and event_to not in compat.get(old_world_to, set()):
                                continue

                            new_world_from = old_world_from + event_from
                            new_world_to = old_world_to + event_to
                            for world, event in [(new_world_from, event_from), (new_world_to, event_to)]:
                                new_worlds.add(world)
                                try:
                                    clusters[event].add(world)
                                except KeyError:
                                    clusters[event] = {world,}
                            try:
                                new_world_links[new_world_from].add(new_world_to)
                            except KeyError:
                                new_world_links[new_world_from] = {new_world_to,}
        return Graph(
            agent_node_links=new_agent_world_links,
            agent_colors=self.agent_colors,
            nodes=new_worlds,
            clusters=clusters,
        )


def parse_compatiblity(f) -> dict[str, str]:
    d = dict()
    for line in f.readlines():
        line = line.strip()
        worlds, _, events = line.partition(' ')
        worlds = worlds.split(',')
        events = events.split(',')
        for world in worlds:
            for event in events:
                try:
                    d[world].add(event)
                except KeyError:
                    d[world] = {event,}
    return d


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("STATES", nargs=1, type=argparse.FileType('r'))
    parser.add_argument("EVENTS", nargs=1, type=argparse.FileType('r'))
    parser.add_argument("COMPAT", nargs=1, type=argparse.FileType('r'))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    states = Graph.from_graphviz(args.STATES[0])
    events = Graph.from_graphviz(args.EVENTS[0])
    compat = parse_compatiblity(args.COMPAT[0])
    new_states = states.product(events, compat)
    print(new_states.to_graphviz())
