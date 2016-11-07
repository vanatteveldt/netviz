import csv
import subprocess
from io import StringIO
import base64

from wtforms import form, fields, widgets
from actionform import ActionForm, webserver

def clean(x):
    return x.strip().replace(" ", "_")

def dot2img(dot, format="png", layout="dot"):
    dotformat = 'png' if format == 'html' else format
    cmd = ['dot', '-T', dotformat,'-K', layout]
    result = subprocess.check_output(cmd, input=dot.encode("utf-8"))
    if format == 'html':
        data = base64.b64encode(result).decode("utf-8")
        result = "<object type='image/png' data='data:image/png;base64,{data}'></object>".format(**locals())
    return result



class Network(ActionForm):
    class form_class(form.Form):
        network = fields.StringField(widget=widgets.TextArea())
        normalize = fields.BooleanField()
        qualabel = fields.BooleanField(label="Include quality in label")
        predlabel = fields.BooleanField(label="Include predicate in label")
        #blue = fields.BooleanField()
        #bw = fields.BooleanField(label="Black & White")
        delimiter = fields.SelectField(choices=[("","autodetect"), (";",";"), (",",","), ("\t","tab")])
    def read_network(self, network, delimiter):
        lines = network.split("\n")
        if not delimiter:
            delimiters = {d : network.count(d) for d in ",;\t"}
            delimiter = sorted(delimiters, key=delimiters.get)[-1]
        return csv.reader(lines, delimiter=delimiter)

    def get_graph(self, r, **options):
        nodes = {}
        edges = []
        maxweight = 0
        for edge in r:
            src, su, obj, pred, q, n = edge + [None]*(6-len(edge))
            if q: q = float(q)
            if n: n = float(n)
            for o in su, obj:
                if o not in nodes:
                    nodes[o] = clean(o)
            edges.append((src, su, obj, pred, q, n))
            if n:
                maxweight = max(maxweight, n)

        dot = ["digraph g {"]
        for label, id in nodes.items():
            dot.append('{id} [label="{label}"];'.format(**locals()))
        for src, su, obj, pred, q, n in edges:
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
            print(kargs)
            kargs = ",".join('{k}="{v}"'.format(**locals()) for (k,v) in kargs.items())
            print(kargs)
            dot.append('{su} -> {obj} [{kargs}];'.format(**locals()))
        dot.append("}")
            
        return "\n".join(dot)
        
    def _run(self, network, delimiter, **options):
        r = self.read_network(network, delimiter)
        dot = self.get_graph(r, **options)
        image = dot2img(dot, format='html')
        return dict(dot=dot, image=image)

    def render_result(self, result):
        return "<pre>{dot}</pre>{image}".format(**result)
        
if __name__ == '__main__':
    Network.run_webserver()