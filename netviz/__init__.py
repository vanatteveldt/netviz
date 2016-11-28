import csv
import collections
import subprocess
from io import StringIO
import base64
import re

from wtforms import form, fields, widgets
from actionform import ActionForm, webserver

def clean(x, subgraph=None):
    x = x.strip().replace(" ", "_")
    x = re.sub("\W", "_", x)
    if subgraph:
        subgraph = clean(str(subgraph))
        x = "_{subgraph}__{x}".format(**locals())
    return x

def dot2img(dot, format="png", layout="dot"):
    dotformat = 'png' if format == 'html' else format
    cmd = ['dot', '-T', dotformat,'-K', layout]
    result = subprocess.check_output(cmd, input=dot.encode("utf-8"))
    if format == 'html':
        data = base64.b64encode(result).decode("utf-8")
        result = "<object type='image/png' data='data:image/png;base64,{data}'></object>".format(**locals())
    return result



class Network(ActionForm):
    default_template = "netviz.html"
    
    class form_class(form.Form):
        network = fields.StringField(widget=widgets.TextArea())
        normalize = fields.BooleanField(label="Normalize weights")
        qualabel = fields.BooleanField(label="Include quality in label")
        predlabel = fields.BooleanField(label="Include predicate in label")
        collapse = fields.BooleanField(label="Collapse arrows between nodes")
        nosubgraphs = fields.BooleanField(label="Don't make subgraphs per source")
        #blue = fields.BooleanField()
        #bw = fields.BooleanField(label="Black & White")
        delimiter = fields.SelectField(choices=[("","autodetect"), (";",";"), (",",","), ("\t","tab")])

        
    def read_network(self, network, delimiter):
        lines = [line.strip(' ') for line in network.split("\n")]
        if not delimiter:
            delimiters = {d : network.count(d) for d in ",;\t"}
            delimiter = sorted(delimiters, key=delimiters.get)[-1]
        return csv.reader(lines, delimiter=delimiter)

    def normalize(self, network):        
        for i, edge in enumerate(network):
            src, su, obj, pred, q, n = edge + [None]*(6-len(edge))
            if i == 0 and su == "subject" and obj == "object":
                continue
            if not su or not obj:
                continue
            if q: q = float(q)
            if n: n = float(n)
            yield src, su, obj, pred, q, n
            
    def collapse(self, r):
        edges = {} # src, su, obj: (totq, totn)
        for src, su, obj, pred, q, n in r:
            key = (src, su, obj)
            if key not in edges:
                edges[key] = [0,0, []]
            if not n: n = 1
            if not q: q = 0
            edges[key][0] += q*n
            edges[key][1] += n
            if pred: edges[key][2] += [pred]
            
        for (src, su, obj), (totq, totn, preds) in edges.items():
            yield src, su, obj, "\\n".join(preds), totq/totn, totn

    def get_graph(self, r, **options):
        edges = collections.defaultdict(list)
        maxweight = 0
        for src, su, obj, pred, q, n in r:
            if options.get('nosubgraphs'):
                src = None
            edges[src and src.strip()].append((su, obj, pred, q, n))
            if n:
                maxweight = max(maxweight, n)

        dot = ["digraph g {"]
        for i, src in enumerate(edges):
            if src:
                dot.append('subgraph cluster_%i {\nlabel="%s";' % (i, src))

            nodes = {}
            for node in set(node for (su, obj, pred, q, n) in edges[src] for node in (su,obj)):
                id = clean(node, i if src else None)
                nodes[node] = id
                dot.append('{id} [label="{node}"];'.format(**locals()))
                
            for su, obj, pred, q, n in edges[src]:
                su = nodes[su]
                obj = nodes[obj]
                kargs = {}
                lbl = []
                if n:
                    if options.get('normalize'):
                        n = n * 5 / maxweight
                    kargs['style'] = 'setlinewidth(%1.3f)' % n
                if q:
                    kargs['color'] = "%1.4f,%1.4f,%1.4f" % (.167 + .167 * q,1,1)
                if options.get('predlabel') and pred:
                    lbl.append(pred)
                if options.get('qualabel') and q is not None:
                    lbl.append("%+1.2f" % q)
                if lbl:
                    kargs['label'] = "\\n".join(lbl)
                kargs = ",".join('{k}="{v}"'.format(**locals()) for (k,v) in kargs.items())
                dot.append('{su} -> {obj} [{kargs}];'.format(**locals()))
            if src:
                dot.append("}")
        dot.append("}")
            
        return "\n".join(dot)
        
    def _run(self, network, delimiter, **options):
        r = self.normalize(self.read_network(network, delimiter))
        if options.get('collapse'):
            r = self.collapse(r)
        dot = self.get_graph(r, **options)
        image = dot2img(dot, format='html')
        return dict(dot=dot, image=image)

    def render_result(self, result, template, context):
        context.update(result)
        return template.render(**context)
        
if __name__ == '__main__':
    Network.run_webserver()
