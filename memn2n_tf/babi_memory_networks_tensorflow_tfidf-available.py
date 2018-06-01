import re
import tarfile
import numpy as np
import tensorflow as tf
from sklearn.utils import shuffle
from functools import reduce
from utils.data import get_file
import pickle

np.random.seed(0)
tf.set_random_seed(1234)

#uをtfidfする場合としない場合に分ける
#時間変化に基づく重み付けの採用

def inference(x, q, n_batch,m_tfidf,u_tfidf,
              vocab_size=None,
              embedding_dim=None,
              story_maxlen=None,
              question_maxlen=None):
    def weight_variable(shape, stddev=0.08):
        initial = tf.truncated_normal(shape, stddev=stddev)
        return tf.Variable(initial)

    def bias_variable(shape):
        initial = tf.zeros(shape, dtype=tf.float32)
        return tf.Variable(initial)

    A = weight_variable([vocab_size, embedding_dim])
    B = weight_variable([vocab_size, embedding_dim])
    C = weight_variable([vocab_size, question_maxlen])
    D = weight_variable([vocab_size, embedding_dim])
    m = tf.nn.embedding_lookup(A, x)
    m_mod = m*m_tfidf
    u = tf.nn.embedding_lookup(B, q)
    u_mod = u*u_tfidf
    c = tf.nn.embedding_lookup(C, x)
    p = tf.nn.softmax(tf.einsum('ijk,ilk->ijl', m_mod, u_mod))
    o = tf.add(p, c)
    o = tf.transpose(o, perm=[0, 2, 1])
    v = tf.nn.embedding_lookup(D, q)
    ou = tf.concat([o, v], axis=-1)

    cell = tf.contrib.rnn.BasicLSTMCell(embedding_dim//2, forget_bias=1.0)
    initial_state = cell.zero_state(n_batch, tf.float32)
    state = initial_state
    outputs = []
    with tf.variable_scope('LSTM'):
        for t in range(question_maxlen):
            if t > 0:
                tf.get_variable_scope().reuse_variables()
            (cell_output, state) = cell(ou[:, t, :], state)
            outputs.append(cell_output)
    output = outputs[-1]
    W = weight_variable([embedding_dim//2, vocab_size], stddev=0.01)
    a = tf.nn.softmax(tf.matmul(output, W))

    return a


def loss(y, t):
    cross_entropy = \
        tf.reduce_mean(-tf.reduce_sum(
                       t * tf.log(tf.clip_by_value(y, 1e-10, 1.0)),
                       reduction_indices=[1]))
    return cross_entropy


def training(loss):
    optimizer = \
        tf.train.AdamOptimizer(learning_rate=0.001, beta1=0.9, beta2=0.999)
    train_step = optimizer.minimize(loss)
    return train_step


def accuracy(y, t):
    correct_prediction = tf.equal(tf.argmax(y, 1), tf.argmax(t, 1))
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
    return accuracy


def tokenize(sent):
    return [x.strip() for x in re.split('(\W+)', sent) if x.strip()]


def parse_stories(lines):
    data = []
    story = []
    for line in lines:
        line = line.strip()
        nid, line = line.split(' ', 1)
        nid = int(nid)
        if nid == 1:
            story = []
        if '\t' in line:
            q, a, supporting = line.split('\t')
            q = tokenize(q)
            substory = [x for x in story if x]
            data.append((substory, q, a))
            story.append('')
        else:
            sent = tokenize(line)
            story.append(sent)
    return data


def get_stories(f, max_length=None):
    def flatten(data):
        return reduce(lambda x, y: x + y, data)

    data = parse_stories(f.readlines())
    data = [(flatten(story), q, answer)
            for story, q, answer in data
            if not max_length or len(flatten(story)) < max_length]
    return data


def vectorize_stories(data, word_indices, story_maxlen, question_maxlen):
    X = []
    Q = []
    A = []
    for story, question, answer in data:
        x = [word_indices[w] for w in story]
        q = [word_indices[w] for w in question]
        a = np.zeros(len(word_indices) + 1)  # パディング用に +1
        a[word_indices[answer]] = 1
        X.append(x)
        Q.append(q)
        A.append(a)

    return (padding(X, maxlen=story_maxlen),
            padding(Q, maxlen=question_maxlen), np.array(A))


def padding(words, maxlen):
    for i, word in enumerate(words):
        words[i] = [0] * (maxlen - len(word)) + word
    return np.array(words)


    
#weight_type 0:tf-idf 1:なし 2:時系列線形重み付け 3: 
def tfidf_vectorize(_inputs_np,tfidf_list,weight_type):
    _inputs_list = _inputs_np.tolist()
    vector_list = []
    size = len(_inputs_list[0])
    for _input in _inputs_list:
        if(weight_type==0):
            vector = [0]*size
            for n in range(size):
                index = _input[n]
                if(index==0):
                    vector[n]=0
                else:
                    vector[n]=tfidf_list[index-1]
                vector_np = np.array(vector).reshape((size,1))
            vector_list.append(vector_np)
        elif(weight_type==1):
            vector = [1]*size
            vector_np = np.array(vector).reshape((size,1))
            vector_list.append(vector_np)
        #elif(weight_type==2):
            
    return np.array(vector_list)
        


if __name__ == '__main__':
    '''
    データ読み込み
    '''
    print('Fetching data...')
    '''
    try:
        path = \
            get_file('babi-tasks-v1-2.tar.gz',
                     url='https://s3.amazonaws.com/text-datasets/babi_tasks_1-20_v1-2.tar.gz')
    except Exception as e:
        raise
    tar = tarfile.open(path)
    
    challenge = 'tasks_1-20_v1-2/en-10k/qa1_single-supporting-fact_{}.txt'
    '''
    
    #test = open("test.txt","r")
    #train = open("train.txt","r")
    
    #train_stories = get_stories(train)
    #test_stories = get_stories(test)

    with open('train.pickle', 'rb') as f:
         train_stories = pickle.load(f)            
    with open('test.pickle', 'rb') as f:
         test_stories = pickle.load(f)   
    with open('tf_idf.pickle', 'rb') as f:
         tfidf = pickle.load(f)
    with open('vocab.pickle', 'rb') as f:
         vocab = pickle.load(f)       

    vocab_size = len(vocab) + 1  # パディング用に +1

    story_maxlen = \
        max(map(len, (x for x, _, _ in train_stories + test_stories)))
    question_maxlen = \
        max(map(len, (x for _, x, _ in train_stories + test_stories)))

    print('Vectorizing data...')
    word_indices = dict((c, i + 1) for i, c in enumerate(vocab))
   
    #0:tf-idf 1:BoW 2:時間依存の重み 3:0と2の複合
    weight_type = 0
    
    inputs_train, questions_train, answers_train = \
        vectorize_stories(train_stories, word_indices,
                          story_maxlen, question_maxlen)

    inputs_test, questions_test, answers_test = \
        vectorize_stories(test_stories, word_indices,
                          story_maxlen, question_maxlen)
    inputs_test_tfidf = tfidf_vectorize(inputs_test,tfidf, weight_type)
    questions_test_tfidf = tfidf_vectorize(questions_test,tfidf, weight_type)

    '''
    モデル設定
    '''
    print('Building model...')
    x = tf.placeholder(tf.int32, shape=[None, story_maxlen])
    m_tfidf = tf.placeholder(tf.float32,shape=[None,story_maxlen,1])
    u_tfidf = tf.placeholder(tf.float32,shape=[None,question_maxlen,1])
    q = tf.placeholder(tf.int32, shape=[None, question_maxlen])
    a = tf.placeholder(tf.float32, shape=[None, vocab_size])
    n_batch = tf.placeholder(tf.int32)
    
    
    y = inference(x, q, n_batch,m_tfidf,u_tfidf,
                  vocab_size=vocab_size,
                  embedding_dim=5,
                  story_maxlen=story_maxlen,
                  question_maxlen=question_maxlen)
    loss = loss(y, a)
    train_step = training(loss)
    acc = accuracy(y, a)

    history = {
        'val_loss': [],
        'val_acc': []
    }

    '''
    モデル学習
    '''
    print('Training model...')
    epochs = 1000
    batch_size = 1
   

    init = tf.global_variables_initializer()
    sess = tf.Session()
    sess.run(init)

    n_batches = len(inputs_train) // batch_size

    for epoch in range(epochs):
        inputs_train_, questions_train_, answers_train_ = \
            shuffle(inputs_train, questions_train, answers_train)
        inputs_train_tfidf_=tfidf_vectorize(inputs_train,tfidf,weight_type)
        questions_train_tfidf_=tfidf_vectorize(questions_train_,tfidf,weight_type)
        for i in range(n_batches):
            start = i * batch_size
            end = start + batch_size
            sess.run(train_step, feed_dict={
                x: inputs_train_[start:end],
                q: questions_train_[start:end],
                a: answers_train_[start:end],
                n_batch: batch_size,
                m_tfidf: inputs_train_tfidf_[start:end],
                u_tfidf: questions_train_tfidf_[start:end]
            })
        # テストデータを用いた評価
        val_loss = loss.eval(session=sess, feed_dict={
            x: inputs_test,
            q: questions_test,
            a: answers_test,
            n_batch: len(inputs_test),
            m_tfidf: inputs_test_tfidf,
            u_tfidf: questions_test_tfidf      
        })
        val_acc = acc.eval(session=sess, feed_dict={
            x: inputs_test,
            q: questions_test,
            a: answers_test,
            n_batch: len(inputs_test),
            m_tfidf: inputs_test_tfidf,
            u_tfidf: questions_test_tfidf  
        })
        

        history['val_loss'].append(val_loss)
        history['val_acc'].append(val_acc)
        print('epoch:', epoch,
              ' validation loss:', val_loss,
              ' validation accuracy:', val_acc)
