#!/bin/bash
set -e

bdir=$(dirname "$0")
source "$bdir/ocrd-cis-lib.sh"

# getopt
ocrd-cis-getopt-new $*
ocrd-cis-log-debug "mets: $METS"
ocrd-cis-log-debug "parameter: $PARAMETER"
ocrd-cis-log-debug "input-file-grp: $OUTPUT_FILE_GRP"
ocrd-cis-log-debug "output-file-grp: $INPUT_FILE_GRP"
ocrd-cis-log-debug "log-level: $LOG_LEVEL"

# run additional ocrs and align them
ocrd-cis-run-ocr "$PARAMETER" "$METS" "$INPUT_FILE_GRP" "OCR-D-CIS-OCR-XXX"
ocrd-cis-log-debug ocrd-cis-align \
		--input-file-grp "$INPUT_FILE_GRP,$OCRFILEGRPS" \
		--output-file-grp "OCR-D-CIS-ALIGN"\
		--mets "$METS" \
		--parameter "$PARAMETER"\
		--log-level "$LOG_LEVEL"
ocrd-cis-align \
		--input-file-grp "$INPUT_FILE_GRP,$OCRFILEGRPS" \
		--output-file-grp "OCR-D-CIS-ALIGN"\
		--mets "$METS" \
		--parameter "$PARAMETER"\
		--log-level "$LOG_LEVEL"

# run post correction over aligned files
jar=$(cat "$PARAMETER" | jq --raw-output .jar)
main="de.lmu.cis.ocrd.cli.Main"
ocrd-cis-log-debug java -Dfile.encoding=UTF-8 -Xmx3g -cp "$jar" "$main" -c post-correct\
	 --log-level "$LOG_LEVEL"\
	 --mets "$METS"\
	 --parameter "$PARAMETER"\
	 --input-file-grp "OCR-D-CIS-ALIGN"\
	 --output-file-grp "$OUTPUT_FILE_GRP"
java -Dfile.encoding=UTF-8 -Xmx3g -cp "$jar" "$main" -c post-correct\
	 --log-level "$LOG_LEVEL"\
	 --mets "$METS"\
	 --parameter "$PARAMETER"\
	 --input-file-grp "OCR-D-CIS-ALIGN"\
	 --output-file-grp "$OUTPUT_FILE_GRP"
