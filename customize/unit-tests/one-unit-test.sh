#!/bin/bash

# Script for running a single matrix unit test.
# Invoke with a single argument, the language name of
# the unit test to be applied.
# Be sure that $CUSTOMIZATIONROOT is set appropriately
# (i.e., to point to the matrix/customize directory you
# intend to test... the unit-tests directory with that
# customize/directory is the one that will be active).
# Much copied from logon/parse.

unset DISPLAY;
unset LUI;

if [ -z "${LOGONROOT}" ]; then
  echo "one-unit-test: unable to determine \$LOGONROOT directory; exit.";
  exit 1;
fi

if [ -z "${CUSTOMIZATIONROOT}" ]; then
  echo "one-unit-test: unable to determine \$CUSTOMIZATIONROOT directory; exit.";
  exit 1;
fi

#
# include a shared set of shell functions and global parameters, including the
# architecture identifier .LOGONOS.
#
. ${LOGONROOT}/etc/library.bash;

date=$(date "+%Y-%m-%d");

count=1;
limit=1000;
best=1000;

# Main log file to look at tsdb output.

LOG="${CUSTOMIZATIONROOT}/unit-tests/logs/tsdb.${date}.log";

if [ -e ${LOG} ]; then
    rm ${LOG};
fi

# Find out which unit test

lgname=$1

# Let the user know what we're doing:

echo "Running unit test $1 on $date";
echo "For [incr tsdb()]'s log output, see $LOG";



# Set skeleton, grammar, gold-standard for comparison, and
# target directory.

skeleton="${CUSTOMIZATIONROOT}/unit-tests/skeletons/$lgname"
skeletons="${CUSTOMIZATIONROOT}/unit-tests/skeletons/"
tsdbhome="${CUSTOMIZATIONROOT}/unit-tests/home/"
gold="gold/$lgname"
grammardir="${CUSTOMIZATIONROOT}/unit-tests/grammars/$lgname"
grammar="$grammardir/matrix/lkb/script"
target="current/$lgname"
log="${CUSTOMIZATIONROOT}/unit-tests/logs/$lgname.$date"

# Check to see if there's a grammar in the way, and if
# so, prompt the user to move it.

if [ -e $grammardir ]; then
    echo "one-unit-test: Move $grammardir, it is in the way; exit.";
    exit 1;
fi

# Invoke customize.py

${CUSTOMIZATIONROOT}/unit-tests/call-customize ${CUSTOMIZATIONROOT} ${CUSTOMIZATIONROOT}/unit-tests/choices/$lgname ${CUSTOMIZATIONROOT}/unit-tests/grammars/$lgname


# Set up a bunch of lisp commands then pipe them to logon/[incr tsdb()]

# I don't see how the following can possibly do anything,
# since nothing has yet invoked [incr tsdb()] or lisp.
# But let's give it a try anyway...

{
  options=":error :exit :wait 300";

  echo "(setf (system:getenv \"DISPLAY\") nil)";

  echo "(setf tsdb::*process-suppress-duplicates* nil)";
  echo "(setf tsdb::*process-raw-print-trace-p* t)";

  echo "(setf tsdb::*tsdb-home* \"$tsdbhome\")";
  echo "(tsdb:tsdb :skeletons \"$skeletons\")";

  echo "(lkb::read-script-file-aux \"$grammar\")";

  echo "(setf target \"$target\")";

  echo "(tsdb:tsdb :create target :skeleton \"$lgname\")";

  echo "(tsdb:tsdb :process target)";

  echo "(tsdb::compare-in-detail \"$target\" \"$gold\" :format :ascii :compare '(:readings :mrs) :append \"$log\")";

} | ${LOGONROOT}/bin/logon ${source} ${cat} \
      -I base -locale no_NO.UTF-8 -qq 2> ${LOG} > ${LOG}

# FIXME: There is probably a more appropriate set of options to
# send to logon, but it seems to work fine as is for now.

echo "What follows are the diffs, if any, for this unit test."

if [ -e $log ]; then
    cat $log;
    rm $log
fi

#Clean up

rm -r $grammardir
rm -r "$tsdbhome/$target"
