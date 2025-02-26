from pathlib import Path

from dotenv import load_dotenv
from pipen import Proc, Pipen

BUCKET = "gs://ml-phi-staff-m161047-p-rsa-us-central1-p-84f8"
load_dotenv(Path(__file__).parent.parent / ".env")


class MyProcess(Proc):

    input = "a"
    input_data = [1]
    output = "outfile:file:{{in.a}}.txt"
    script = "echo {{in.a}} > {{out.outfile}}"


# Works even when metadir/outdir mounted
class MyProcess2(Proc):
    requires = MyProcess
    input = "infile:file"
    output = "outfile:file:{{in.infile.stem}}2.txt"
    script = "echo 123 > {{out.outfile}}"
    export = True


# Works even when metadir/outdir mounted
class MyProcess3(Proc):
    requires = MyProcess2
    input = "infile:file"
    output = "outfile:file:{{in.infile.stem}}3.txt"
    script = "echo 456 > {{out.outfile}}"


class MyGBatchPipeline(Pipen):
    starts = MyProcess
    workdir = f"{BUCKET}/pipen-test/workdir"
    outdir = f"{BUCKET}/pipen-test/outdir"
    loglevel = "DEBUG"


if __name__ == "__main__":
    MyGBatchPipeline().run(profile="gbatch")
