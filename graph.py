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
        for event, nodes in (self.clusters or dict()).items():
            yield ""
            yield f"  subgraph cluster_{event} {{"
            for node in nodes:
                yield f"    {node};"
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
        new_agent_node_links = dict()
        new_nodes = set()
        clusters = dict()
        for agent, node_links in self.agent_node_links.items():
            new_agent_node_links[agent] = dict()
            for node_from, nodes_to in node_links.items():
                for node_to in nodes_to:
                    for event_from, events_to in events.agent_node_links[agent].items():
                        if event_from not in compat[node_from]:
                            continue
                        for event_to in events_to:
                            if event_to not in compat[node_to]:
                                continue
                        try:
                            if event_to in events.agent_node_links[agent][event_from]:
                                new_node_from = node_from + event_from
                                new_node_to = node_to + event_to
                                for node, event in [(new_node_from, event_from), (new_node_to, event_to)]:
                                    new_nodes.add(node)
                                    try:
                                        clusters[event].add(node)
                                    except KeyError:
                                        clusters[event] = {node,}
                                try:
                                    new_agent_node_links[agent][new_node_from].add(new_node_to)
                                except KeyError:
                                    new_agent_node_links[agent][new_node_from] = {new_node_to,}
                        except KeyError:
                            pass
        return Graph(agent_node_links=new_agent_node_links, agent_colors=self.agent_colors, nodes=new_nodes, clusters=clusters)


def parse_compatiblity(f) -> dict[str, str]:
    d = dict()
    for line in f.readlines():
        line = line.strip()
        worlds, _, events = line.partition(' ')
        worlds = worlds.split(',')
        events = events.split(',')
        events.append('true')
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
    '''
    from pprint import pprint
    for model in (state_model, event_model):
        pprint(model.agent_node_links)
        print(model.to_graphviz())
    pprint(compatibility)
    '''
    new_states = states.product(events, compat)
    print(new_states.to_graphviz())
