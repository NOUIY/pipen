from pathlib import Path

from dotenv import load_dotenv
from pipen import Proc, Pipen

BUCKET = "gs://ml-phi-staff-m161047-p-rsa-us-central1-p-84f8"
load_dotenv(Path(__file__).parent.parent / ".env")


class MyProcess(Proc):
    """A process using mako templating"""

    input = "a"
    input_data = [1]
    output = "outfile:file:{{in.a}}.txt"
    script = "ls -l {{job.outdir}}; touch {{out.outfile}}"


class MyGBatchPipeline(Pipen):
    starts = MyProcess
    workdir = f"{BUCKET}/pipen-test/workdir"
    outdir = f"{BUCKET}/pipen-test/outdir"
    loglevel = "DEBUG"


if __name__ == "__main__":
    MyGBatchPipeline().run(profile="gbatch")
