#!/bin/bash
set -e

bdir=$(dirname "$0")
source "$bdir/ocrd-cis-lib.sh"

ocrd-cis-getopt-new $*

# run additional ocrs and align them
ocrd-cis-run-ocr "$PARAMETER" "$METS" "$INPUT_FILE_GRP" "OCR-D-CIS-OCR-XXX"
ocrd-cis-align \
		--input-file-grp "$INPUT_FILE_GRP $OCRFILEGRPS" \
		--output-file-grp "OCR-D-CIS-ALIGN"\
		--mets "$METS" \
		--parameter "$PARAMETER"\
		--log-level "$LOG_LEVEL"

# run post correction over aligned files
jar=$(cat "$PARAMETER" | jq --raw-output .jar)
main="de.lmu.cis.ocrd.cli.Main"
java -Dfile.encoding=UTF-8 -Xmx3g -cp "$jar" "$main" -c post-correct\
	 --log-level "$LOG_LEVEL"\
	 --mets "$METS"\
	 --parameter "$PARAMETER"\
	 --input-file-grp "OCR-D-CIS-ALIGN"\
	 --output-file-grp "$OUTPUT_FILE_GRP"
